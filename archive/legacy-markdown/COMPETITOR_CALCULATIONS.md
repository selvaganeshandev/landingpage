# Competitor Page - Calculation Methods

This document explains how all values are calculated in the Competitor Analysis page.

## Overview Tab

### 1. Competitor Cards (Top 3 shown in overview, all in Competitors tab)

**Data Source**: `/competitors/competitors/by_domain/?domain_id={id}` (includes "You" as first item)

#### Metrics Displayed:

- **Mentions**: `c.total_mentions || 0`
  - Direct from API: `total_mentions` field from Competitor/Domain model
  - For "You": Uses `domain.total_mentions`
  - For Competitors: Uses `competitor.total_mentions`

- **Visibility**: `Math.round(Number(c.visibility_score || 0))`
  - Direct from API: `visibility_score` field (0-100 scale)
  - For "You": Uses `domain.visibility_score`
  - For Competitors: Uses `competitor.visibility_score`
  - Backend calculation: Based on mentions, citations, sentiment, and average position

- **Sentiment**: `Math.round((rawSentiment + 1) * 50)`
  - Source: `sentiment_score` from API (range: -1 to 1)
  - Formula: `(sentiment_score + 1) * 50` to convert to 0-100 percentage
  - For "You": Uses `domain.sentiment_score`
  - For Competitors: Uses `competitor.sentiment_score`
  - Backend: Weighted average of all mention sentiment scores

- **Average Position**: `Number(c.average_position || 0).toFixed(1)`
  - Direct from API: `average_position` field
  - For "You": Uses `domain.average_position`
  - For Competitors: Uses `competitor.average_position`
  - Backend: Average of all mention positions (lower is better)

- **Share of Voice**: `Math.round(Number(c.share_of_voice_percentage || 0))`
  - Direct from API: `share_of_voice_percentage` field (0-100)
  - For "You": From `ShareOfVoiceAnalytics` where `competitor__isnull=True`
  - For Competitors: From `ShareOfVoiceAnalytics` where `competitor_id` matches
  - Backend calculation: `(brand_mentions / total_market_mentions) * 100`

- **Trend**: `Number(c.trend_percentage || 0)`
  - Direct from API: `trend_percentage` field
  - Backend: Percentage change in mentions compared to previous period

### 2. Brand Visibility Over Time Chart

**Data Source**: `/analytics/share-of-voice/by_domain/?domain_id={id}&days={timePeriod}`

**Calculation**:
- Groups data by `timestamp` (month/date)
- For each timestamp, sums `mention_count` by brand
- Brands identified by: `r.brand_name || r.competitor?.name || (r.is_you ? 'You' : 'Your Brand')`
- Chart shows line for each brand over time
- X-axis: Timestamp (month)
- Y-axis: Total mentions for that brand on that date

### 3. Competitor Analysis Heatmap

**Data Source**: Latest date from share of voice data (filtered by `timePeriod`)

**Calculation**:
- Filters rows to latest date: `rows.filter((r: any) => (r.timestamp || r.date) === lastDate)`
- Groups by platform and brand
- For each platform, calculates percentage: `(brand_mentions / total_platform_mentions) * 100`
- Shows top 3 brands per platform
- Heatmap cells show percentage (0-100%)

### 4. Top Brands by Visibility

**Data Source**: `/api/share-of-voice/?domain_id={id}` (engine API - latest snapshot)

**Calculation**:
- From `latest?.players` array
- Maps each player to: `{ name, mentions, percentage, isYou }`
- **Deduplication**: Uses Map to prevent duplicate brand names (keeps entry with highest mentions)
- Sorts: "You" first, then by mentions (descending)
- Shows top 5 brands
- **Mentions**: `p?.mention_count || 0`
- **Percentage**: `Number(p?.share_percentage || 0)`

### 5. Competitive Strength Analysis (Radar Chart)

**Data Source**: `/competitors/competitive-strength-analysis?domain_id={id}`

**Metrics** (all normalized to 0-100 scale):

- **Visibility**: 
  - For "You": `100.0 - (your_avg_position * 20.0)` (clamped 0-100)
  - For Competitors: `competitor.visibility_score` (already 0-100)

- **Sentiment**:
  - For "You": `your_sentiment * 100` (sentiment_score is -1 to 1, converted to 0-100)
  - For Competitors: `competitor.sentiment_score * 100`

- **Position** (inverted - lower position is better):
  - For "You": `100.0 - (your_avg_position * 10.0)` (clamped 0-100)
  - For Competitors: `100.0 - (competitor.average_position * 10.0)` (clamped 0-100)

- **Coverage**:
  - For "You": `(your_mentions / total_prompts) * 100`
  - For Competitors: `(comp_mentioned / comp_total_prompts) * 100`

- **Growth**:
  - For "You": `((last_30_count - prev_30_count) / prev_30_count) * 100`
  - For Competitors: `((last_30_sum - prev_30_sum) / prev_30_sum) * 100`

### 6. Competitive Intelligence Insights

**Data Source**: `/competitors/competitive-insights?domain_id={id}`

**Calculation**: Backend analyzes data and generates insights based on:
- Market leadership comparisons
- Sentiment advantages
- Competitor momentum (growth rates)
- Opportunity gaps (prompts where competitors appear but you don't)

## Prompts Tab

### Prompt Performance Analysis

**Data Source**: `/api/competitor-prompt-analytics/?domain_id={id}` (engine API)

**Calculation**:
- Groups by prompt text
- For each prompt, counts mentions per brand
- Shows top 3 brands (You + top 2 competitors)
- **Total mentions**: Sum of all brand mentions for that prompt
- **Per-brand mentions**: Count from `CompetitorPromptAnalytics` records
- **Winner**: Brand with highest mention count for that prompt
- Progress bars show: `(brand_mentions / total_mentions) * 100`

**Load More**: Shows 10 prompts initially, "Load More" button adds 10 more

## Competitors Tab

**Data Source**: Same as Overview competitor cards, but shows ALL competitors (not limited to 3)

**Metrics**: Same calculations as Overview competitor cards

## Answer Gap Tab

**Data Source**: `/competitors/answer-gap-analysis?domain_id={id}`

**Calculation**:
- Finds prompts where competitors are mentioned (position ≤ 10) but "You" is not mentioned
- Groups by prompt
- Shows: query text, competitor name, total competitor mentions, your mentions, opportunity level
- Opportunity levels:
  - High: `total_comp_mentions >= 50 && your_mentions == 0`
  - Medium: `total_comp_mentions >= 30 && your_mentions < 5`
  - Low: Otherwise

## Date Filtering

**Applied to**:
- Share of Voice by Domain API: `days={timePeriod}` parameter
- All time-series charts and data respect the selected time period
- Latest snapshot data (Top Brands, Heatmap) uses the most recent date within the filtered period

**Time Period Options**:
- 7 days
- 30 days
- 90 days
- 365 days

## Notes

1. **"You" vs Competitors**: "You" is always included as the first item in all lists
2. **Deduplication**: Top Brands list uses Map to prevent duplicate entries
3. **Sorting**: "You" is always sorted first, then by relevant metric (mentions, share, etc.)
4. **Data Sources**: Mix of backend APIs (port 8000) and engine APIs (port 8001)
5. **Real-time Updates**: Data refreshes when `domainId` or `timePeriod` changes

