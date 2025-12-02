# Traffic Page Documentation

## Overview
The Traffic Attribution page (`/traffic`) displays traffic data from Google Analytics (GA) and Google Search Console (GSC) to track and attribute traffic from AI platforms and measure ROI.

## Page Components

### 1. **ROI Metrics Cards** (Top Section)
Displays 4 key metrics:
- **Total Traffic from AI**: Total sessions/visits from AI platforms
- **Conversion Rate**: Percentage of traffic that converts
- **Total Revenue**: Total revenue generated from AI traffic
- **ROI**: Return on investment (currently shows "N/A")

**Data Source**: Google Analytics
- `total_sessions` from GA insights
- `total_conversions` / `total_sessions` * 100
- `total_revenue` from GA insights

**Where to find in GA**: 
- **Reports** → **Engagement** → **Overview** → Filter by Source/Medium
- Or **Reports** → **Acquisition** → **Traffic acquisition** → Filter by source containing AI platforms

---

### 2. **Traffic Sources Tab**
Shows AI platform referral analysis with:
- Platform name (ChatGPT, Perplexity, Claude, Gemini, etc.)
- Visits/Sessions
- Conversions
- Revenue
- Bounce Rate
- Average Session Duration

**Data Source**: Google Analytics
- `platform_breakdown` JSON field from `GATrafficInsight` model
- Fetched via `_fetch_platform_breakdown()` method

**Where to find in GA**:
- **Reports** → **Acquisition** → **Traffic acquisition**
- Filter by Source dimension
- Look for sources like: `chat.openai.com`, `claude.ai`, `gemini.google.com`, `perplexity.ai`

**API Method**: `engine/core/ga_insights_processor.py::_fetch_platform_breakdown()`
- Uses GA4 Data API: `properties().runReport()`
- Dimensions: `sessionSource`, `sessionMedium`
- Metrics: `sessions`, `conversions`, `totalRevenue`, `bounceRate`, `averageSessionDuration`
- Filters: `sessionSource` contains AI platform domains

---

### 3. **Search Console Tab**
Displays top search queries driving traffic:
- Query text
- Impressions
- Clicks
- CTR (Click-Through Rate)
- Average Position

**Data Source**: Google Search Console
- `top_queries` JSON field from `GSCTrafficInsight` model
- Fetched via `_fetch_top_queries()` method

**Where to find in GSC**:
- **Performance** → **Search results**
- View by "Queries" dimension
- Shows top queries with impressions, clicks, CTR, and position

**API Method**: `engine/core/gsc_insights_processor.py::_fetch_top_queries()`
- Uses GSC API: `searchanalytics().query()`
- Endpoint: `POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query`
- Dimensions: `['query']`
- Metrics: `impressions`, `clicks`, `ctr`, `position`
- Ordered by clicks (DESCENDING)

---

### 4. **Devices & Geo Tab**
Two side-by-side cards:

#### Device Breakdown
- Device type (Desktop, Mobile, Tablet)
- Sessions count
- Percentage of total
- Conversions
- Revenue

**Data Source**: Google Analytics
- `device_breakdown` JSON field from `GATrafficInsight` model
- Fetched via `_fetch_device_breakdown()` method

**Where to find in GA**:
- **Reports** → **Tech** → **Tech details**
- Or **Reports** → **User** → **Tech** → **Device category**
- Filter by Source/Medium for AI traffic

**API Method**: `engine/core/ga_insights_processor.py::_fetch_device_breakdown()`
- Dimensions: `deviceCategory`
- Metrics: `sessions`, `conversions`, `totalRevenue`

#### Geographic Distribution
- Country name
- Sessions count
- Percentage of total
- Revenue

**Data Source**: Google Analytics
- `geographic_breakdown` JSON field from `GATrafficInsight` model
- Fetched via `_fetch_geographic_breakdown()` method

**Where to find in GA**:
- **Reports** → **User** → **Demographics details** → **Demographics overview**
- Or **Reports** → **User** → **Geo** → **Location**
- Filter by Source/Medium for AI traffic

**API Method**: `engine/core/ga_insights_processor.py::_fetch_geographic_breakdown()`
- Dimensions: `country`
- Metrics: `sessions`, `totalRevenue`

---

### 5. **Landing Pages Tab**
Shows top landing pages from AI traffic:
- Page URL
- Sessions
- Bounce Rate
- Average Duration
- Conversions

**Data Source**: Google Analytics
- `landing_pages` JSON field from `GATrafficInsight` model
- Fetched via `_fetch_landing_pages()` method

**Where to find in GA**:
- **Reports** → **Engagement** → **Pages and screens**
- Filter by Source/Medium for AI traffic
- Shows landing pages with session metrics

**API Method**: `engine/core/ga_insights_processor.py::_fetch_landing_pages()`
- Dimensions: `landingPage`
- Metrics: `sessions`, `bounceRate`, `averageSessionDuration`, `conversions`

---

### 6. **Attribution Models Tab**
Shows revenue attribution across different models:
- First Touch (35% of revenue)
- Last Touch (29% of revenue)
- Linear (21% of revenue)
- Time Decay (15% of revenue)

**Data Source**: Calculated from Google Analytics revenue
- Currently uses mock percentages
- Based on `total_revenue` from GA insights

**Where to find in GA**:
- **Reports** → **Attribution** → **Model comparison**
- Shows how different attribution models assign credit to touchpoints

**Note**: This is currently using calculated/mock data. Real attribution data would require GA4 Attribution API integration.

---

## Data Flow

### 1. **Frontend Request**
```typescript
// frontend/src/pages/TrafficAttribution.tsx
const data = await apiClient.getTrafficInsights(selectedDomain.id);
```

### 2. **Backend API Endpoint**
```python
# backend/integrations/views.py
GET /api/integrations/traffic-insights/?domain_id={domain_id}
```

### 3. **Data Retrieval**
The backend fetches the latest completed insights:
- **GA Data**: From `GATrafficInsight` model where `track_status='COMP'`
- **GSC Data**: From `GSCTrafficInsight` model where `track_status='COMP'`

### 4. **Data Processing (Background)**
Data is fetched from APIs in the background via Celery tasks:

#### Google Analytics Processing
- **Processor**: `engine/core/ga_insights_processor.py`
- **Task**: `process_ga_insight_task` (Celery shared task)
- **Trigger**: Manual via `/integrations/start/` endpoint or scheduled
- **API**: GA4 Data API (`analyticsdata` v1beta)
- **Property ID**: Stored in `Integration.provider_id`

#### Google Search Console Processing
- **Processor**: `engine/core/gsc_insights_processor.py`
- **Task**: `process_gsc_insight_task` (Celery shared task)
- **Trigger**: Manual via `/integrations/start/` endpoint or scheduled
- **API**: GSC API (`searchconsole` v1)
- **Site URL**: Stored in `Integration.provider_id`

---

## Google Analytics API Details

### Authentication
- **OAuth 2.0** with refresh tokens
- Stored in `Integration.credentials` JSON field
- Scopes: `https://www.googleapis.com/auth/analytics.readonly`

### API Endpoint
```
POST https://analyticsdata.googleapis.com/v1beta/properties/{propertyId}:runReport
```

### Key Metrics Fetched
1. **Overall Metrics**:
   - `sessions`
   - `totalUsers`
   - `screenPageViews`
   - `conversions`
   - `totalRevenue`
   - `bounceRate`
   - `averageSessionDuration`

2. **Platform Breakdown**:
   - Dimensions: `sessionSource`, `sessionMedium`
   - Filters: AI platform domains (chat.openai.com, claude.ai, etc.)

3. **Device Breakdown**:
   - Dimensions: `deviceCategory`
   - Metrics: `sessions`, `conversions`, `totalRevenue`

4. **Geographic Breakdown**:
   - Dimensions: `country`
   - Metrics: `sessions`, `totalRevenue`

5. **Landing Pages**:
   - Dimensions: `landingPage`
   - Metrics: `sessions`, `bounceRate`, `averageSessionDuration`, `conversions`

### Where to Find in Google Analytics UI

1. **Overall Traffic**:
   - **Reports** → **Engagement** → **Overview**
   - Date range selector at top

2. **Platform/Source Breakdown**:
   - **Reports** → **Acquisition** → **Traffic acquisition**
   - Click on "Session source" dimension
   - Filter or search for AI platforms

3. **Device Breakdown**:
   - **Reports** → **Tech** → **Tech details**
   - Or **Reports** → **User** → **Tech** → **Device category**

4. **Geographic Data**:
   - **Reports** → **User** → **Geo** → **Location**
   - Shows countries with session counts

5. **Landing Pages**:
   - **Reports** → **Engagement** → **Pages and screens**
   - Shows pages with engagement metrics

---

## Google Search Console API Details

### Authentication
- **OAuth 2.0** with refresh tokens
- Stored in `Integration.credentials` JSON field
- Scopes: `https://www.googleapis.com/auth/webmasters.readonly`

### API Endpoint
```
POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query
```

### Key Data Fetched
1. **Overall Metrics**:
   - `impressions`
   - `clicks`
   - `ctr` (calculated: clicks/impressions * 100)
   - `position` (average)

2. **Top Queries**:
   - Dimension: `query`
   - Ordered by clicks (DESCENDING)
   - Limit: 10 (configurable)

3. **Top Pages**:
   - Dimension: `page`
   - Ordered by clicks (DESCENDING)
   - Limit: 10 (configurable)

4. **Device Breakdown**:
   - Dimension: `device`
   - Metrics: `impressions`, `clicks`, `ctr`, `position`

5. **Country Breakdown**:
   - Dimension: `country`
   - Metrics: `impressions`, `clicks`, `ctr`, `position`

### Where to Find in Google Search Console UI

1. **Overall Performance**:
   - **Performance** → **Search results**
   - Overview shows total impressions, clicks, CTR, position

2. **Top Queries**:
   - **Performance** → **Search results**
   - Click on "Queries" tab
   - Shows search queries with metrics

3. **Top Pages**:
   - **Performance** → **Search results**
   - Click on "Pages" tab
   - Shows pages with search performance metrics

4. **Device Breakdown**:
   - **Performance** → **Search results**
   - Click on "Devices" tab
   - Shows performance by device type

5. **Country Breakdown**:
   - **Performance** → **Search results**
   - Click on "Countries" tab
   - Shows performance by country

---

## Database Models

### GATrafficInsight
Stores processed Google Analytics data:
- `domain`: ForeignKey to Domain
- `integration`: ForeignKey to Integration
- `start_date`, `end_date`: Date range
- `total_sessions`, `total_users`, `total_page_views`
- `total_conversions`, `total_revenue`
- `bounce_rate`, `avg_session_duration`
- `platform_breakdown`: JSON (AI platform breakdown)
- `device_breakdown`: JSON (device category breakdown)
- `geographic_breakdown`: JSON (country breakdown)
- `landing_pages`: JSON (top landing pages)
- `conversion_paths`: JSON (conversion paths)
- `track_status`: Processing status (INIT, PROC, COMP, FAIL)

### GSCTrafficInsight
Stores processed Google Search Console data:
- `domain`: ForeignKey to Domain
- `integration`: ForeignKey to Integration
- `start_date`, `end_date`: Date range
- `total_impressions`, `total_clicks`
- `avg_ctr`, `avg_position`
- `top_queries`: JSON (top search queries)
- `top_pages`: JSON (top pages)
- `device_breakdown`: JSON (device breakdown)
- `country_breakdown`: JSON (country breakdown)
- `track_status`: Processing status (INIT, PROC, COMP, FAIL)

---

## Setup Requirements

1. **Google Analytics Integration**:
   - Connect GA4 property via Domain Settings → Integrations
   - OAuth authentication required
   - Property must be selected

2. **Google Search Console Integration**:
   - Connect GSC site via Domain Settings → Integrations
   - OAuth authentication required
   - Site must be verified in GSC
   - Site must be selected

3. **Data Processing**:
   - Trigger processing via `/integrations/start/` endpoint
   - Or wait for scheduled processing (if configured)
   - Processing happens in background via Celery

---

## API Endpoints

### Get Traffic Insights
```
GET /api/integrations/traffic-insights/?domain_id={domain_id}
```
Returns latest GA and GSC insights for the domain.

### Start Traffic Processing
```
POST /api/integrations/start/
Body: { "integration_id": 1, "days_back": 30 }
```
Triggers background processing of GA and GSC data.

---

## File Locations

### Frontend
- **Page Component**: `frontend/src/pages/TrafficAttribution.tsx`
- **API Client**: `frontend/src/services/api.ts` (getTrafficInsights method)

### Backend
- **API View**: `backend/integrations/views.py` (get_traffic_insights function)
- **URL Routing**: `backend/integrations/urls.py`
- **Models**: `backend/integrations/models.py` (GATrafficInsight, GSCTrafficInsight)

### Engine (Processing)
- **GA Processor**: `engine/core/ga_insights_processor.py`
- **GSC Processor**: `engine/core/gsc_insights_processor.py`
- **Processing Tasks**: `engine/core/processing_tasks.py`
- **OAuth Helper**: `engine/integrations/google_oauth_helper.py`

---

## Notes

1. **Data Freshness**: Data is processed in the background. The page shows the latest completed insights, which may be from a previous processing run.

2. **Empty States**: If no data is available, the page shows an empty state with a link to set up integrations.

3. **Attribution Models**: Currently uses calculated percentages. Real attribution data would require GA4 Attribution API integration.

4. **Rate Limits**: 
   - GA4: 100 requests per 100 seconds per project
   - GSC: 1000 requests per day per site

5. **Date Ranges**: Default is last 30 days. Can be configured when triggering processing.

