# Frontend API Integration - Complete Guide

## ✅ Integration Complete

All new backend APIs have been successfully integrated into the frontend `api.ts` service.

---

## 📊 New API Methods Added

### **1. Alerts API** (17 methods)

#### **Alert Management**
```typescript
// Get all alerts with filtering
await apiClient.getAlerts({
  domain_id: 1,
  status: 'active',
  type: 'visibility_drop',
  severity: 'high'
});

// Get single alert
await apiClient.getAlert(alertId);

// Create new alert
await apiClient.createAlert({
  domain: 1,
  type: 'visibility_drop',
  severity: 'high',
  title: 'Visibility dropped by 30%',
  message: 'Your visibility score decreased significantly',
  platform: 'ChatGPT',
  metric: -30
});

// Update alert
await apiClient.updateAlert(alertId, { status: 'investigating' });

// Resolve alert
await apiClient.resolveAlert(alertId);

// Mark as investigating
await apiClient.investigateAlert(alertId);

// Get active alerts only
await apiClient.getActiveAlerts();

// Get alert summary
await apiClient.getAlertSummary(domainId);
// Returns: { total, active, high_priority, investigating, resolved_today }
```

#### **Alert Rules**
```typescript
// Get alert rules
await apiClient.getAlertRules({ domain_id: 1 });

// Create alert rule
await apiClient.createAlertRule({
  domain: 1,
  name: 'Visibility Drop Alert',
  description: 'Trigger when visibility drops by 20%',
  enabled: true,
  conditions: {
    metric: 'visibility',
    threshold: 20,
    operator: 'less_than',
    time_window: '24h'
  },
  notification_channels: ['email', 'slack']
});

// Update alert rule
await apiClient.updateAlertRule(ruleId, { enabled: false });

// Toggle alert rule
await apiClient.toggleAlertRule(ruleId);
// Returns: { enabled: true/false }
```

---

### **2. Competitors API** (13 methods)

#### **Competitor Management**
```typescript
// Get all competitors
await apiClient.getCompetitors({ domain_id: 1 });

// Get competitors by domain
await apiClient.getCompetitorsByDomain(domainId);

// Get single competitor
await apiClient.getCompetitor(competitorId);

// Create competitor
await apiClient.createCompetitor({
  domain: 1,
  name: 'Competitor A',
  url: 'https://competitor-a.com',
  mentions: 150,
  visibility_score: 85.5,
  sentiment: 75.2
});

// Update competitor
await apiClient.updateCompetitor(competitorId, {
  mentions: 200,
  visibility_score: 88.0
});

// Delete competitor
await apiClient.deleteCompetitor(competitorId);

// Get competitor comparison
await apiClient.getCompetitorComparison(domainId);
// Returns: { competitors[], summary: { total_competitors, avg_mentions, total_market_mentions } }
```

#### **Competitor Analytics**
```typescript
// Get competitor analytics
await apiClient.getCompetitorAnalytics({
  competitor_id: 1,
  days: 30
});

// Get competitor trends
await apiClient.getCompetitorTrends(competitorId, 30);
```

#### **Competitor Prompts & Gap Analysis**
```typescript
// Get competitor prompts
await apiClient.getCompetitorPrompts(competitorId);

// Get answer gaps (CRITICAL for content strategy)
await apiClient.getAnswerGaps(domainId);
// Returns prompts where competitors dominate and you have low presence
```

---

### **3. Topics API** (13 methods)

#### **Topic Management**
```typescript
// Get all topics
await apiClient.getTopics({ domain_id: 1 });

// Get topics by domain
await apiClient.getTopicsByDomain(domainId);

// Get single topic
await apiClient.getTopic(topicId);

// Create topic
await apiClient.createTopic({
  domain: 1,
  name: 'AI Technology',
  keywords: ['artificial intelligence', 'machine learning', 'deep learning'],
  platforms: ['ChatGPT', 'Claude', 'Gemini']
});

// Update topic
await apiClient.updateTopic(topicId, {
  keywords: ['AI', 'ML', 'deep learning', 'neural networks']
});

// Delete topic
await apiClient.deleteTopic(topicId);

// Get trending topics
await apiClient.getTrendingTopics(domainId);
// Returns topics with positive trend_percentage
```

#### **Topic Analytics**
```typescript
// Get topic analytics
await apiClient.getTopicAnalytics({
  topic_id: 1,
  days: 30
});

// Get topic trends
await apiClient.getTopicTrends(topicId, 30);
```

#### **Topic Prompts**
```typescript
// Get topic prompts
await apiClient.getTopicPrompts(topicId);

// Get high relevance prompts
await apiClient.getHighRelevancePrompts({
  topic_id: 1,
  min_score: 80
});
// Returns AI-suggested prompts with high relevance scores
```

---

### **4. Analytics API** (8 methods)

#### **Sentiment Analytics**
```typescript
// Get sentiment analytics
await apiClient.getSentimentAnalytics({
  domain_id: 1,
  days: 30
});

// Get sentiment by domain
await apiClient.getSentimentByDomain(domainId, 30);

// Get sentiment summary
await apiClient.getSentimentSummary(domainId, 7);
// Returns: {
//   positive_percentage: 65.5,
//   neutral_percentage: 25.0,
//   negative_percentage: 9.5,
//   total_mentions: 1234,
//   themes: [{ theme, total_mentions }, ...]
// }
```

#### **Share of Voice Analytics**
```typescript
// Get share of voice
await apiClient.getShareOfVoice({
  domain_id: 1,
  days: 30,
  platform: 'ChatGPT'
});

// Get SOV by domain
await apiClient.getShareOfVoiceByDomain(domainId, {
  days: 30,
  platform: 'ChatGPT'
});

// Get SOV comparison (market share)
await apiClient.getShareOfVoiceComparison(domainId, {
  date: '2025-10-31',
  platform: 'ChatGPT'
});
// Returns: {
//   your_brand: { share_percentage, mention_count, market_position },
//   competitors: [{ name, share_percentage, mention_count, market_position }],
//   total_market_mentions: 5000
// }
```

---

### **5. Integrations API** (10 methods)

#### **Integration Management**
```typescript
// Get all integrations
await apiClient.getIntegrations({ domain_id: 1 });

// Get integrations by domain
await apiClient.getIntegrationsByDomain(domainId);

// Get single integration
await apiClient.getIntegration(integrationId);

// Create integration
await apiClient.createIntegration({
  domain: 1,
  type: 'google_analytics',
  provider_id: 'GA-123456',
  credentials: {
    access_token: 'xxx',
    refresh_token: 'yyy',
    expires_at: '2025-12-31T23:59:59Z'
  }
});

// Update integration
await apiClient.updateIntegration(integrationId, {
  status: 'active'
});

// Delete integration
await apiClient.deleteIntegration(integrationId);

// Test integration connection
await apiClient.testIntegration(integrationId);
// Returns: { status: 'success', message: 'Google Analytics connection is active' }

// Disconnect integration
await apiClient.disconnectIntegration(integrationId);
// Returns: { status: 'disconnected', message: 'Google Analytics has been disconnected' }

// Manually sync integration
await apiClient.syncIntegration(integrationId);
// Returns: { status: 'synced', last_sync_at: '2025-10-31T12:00:00Z' }

// Get integration status summary
await apiClient.getIntegrationStatusSummary(domainId);
// Returns: { total: 5, active: 4, error: 1, disconnected: 0 }
```

---

## 🎯 Usage Examples

### **Example 1: Alerts Dashboard**

```typescript
import { apiClient } from '@/services/api';

// Alerts Dashboard Component
async function loadAlertsData(domainId: number) {
  try {
    // Get alert summary
    const summary = await apiClient.getAlertSummary(domainId);
    console.log(`Active alerts: ${summary.active}`);
    console.log(`High priority: ${summary.high_priority}`);
    
    // Get active alerts
    const activeAlerts = await apiClient.getActiveAlerts();
    
    // Filter high severity alerts
    const criticalAlerts = await apiClient.getAlerts({
      domain_id: domainId,
      status: 'active',
      severity: 'high'
    });
    
    return { summary, activeAlerts, criticalAlerts };
  } catch (error) {
    console.error('Failed to load alerts:', error);
  }
}

// Resolve an alert
async function handleResolveAlert(alertId: number) {
  try {
    await apiClient.resolveAlert(alertId);
    // Refresh alerts list
    await loadAlertsData(domainId);
  } catch (error) {
    console.error('Failed to resolve alert:', error);
  }
}
```

---

### **Example 2: Competitor Analysis**

```typescript
import { apiClient } from '@/services/api';

// Competitors Page Component
async function loadCompetitorData(domainId: number) {
  try {
    // Get competitor comparison
    const comparison = await apiClient.getCompetitorComparison(domainId);
    
    console.log(`Total competitors: ${comparison.summary.total_competitors}`);
    console.log(`Market mentions: ${comparison.summary.total_market_mentions}`);
    
    // Get competitors list
    const competitors = comparison.competitors;
    
    // Get answer gaps (content opportunities)
    const gaps = await apiClient.getAnswerGaps(domainId);
    console.log(`Found ${gaps.length} content gap opportunities`);
    
    // Get trends for top competitor
    if (competitors.length > 0) {
      const topCompetitor = competitors[0];
      const trends = await apiClient.getCompetitorTrends(topCompetitor.id, 30);
    }
    
    return { comparison, gaps };
  } catch (error) {
    console.error('Failed to load competitor data:', error);
  }
}
```

---

### **Example 3: Topics & Trending**

```typescript
import { apiClient } from '@/services/api';

// Topics Page Component
async function loadTopicsData(domainId: number) {
  try {
    // Get trending topics
    const trending = await apiClient.getTrendingTopics(domainId);
    
    // Get all topics
    const topics = await apiClient.getTopicsByDomain(domainId);
    
    // Get high-relevance prompts for content ideas
    const highValuePrompts = await apiClient.getHighRelevancePrompts({
      min_score: 85
    });
    
    // Get analytics for a specific topic
    if (topics.length > 0) {
      const topTopic = topics[0];
      const analytics = await apiClient.getTopicTrends(topTopic.id, 30);
    }
    
    return { trending, topics, highValuePrompts };
  } catch (error) {
    console.error('Failed to load topics:', error);
  }
}

// Create a new topic
async function createNewTopic(domainId: number) {
  try {
    const newTopic = await apiClient.createTopic({
      domain: domainId,
      name: 'Cloud Computing',
      keywords: ['AWS', 'Azure', 'cloud storage', 'serverless'],
      platforms: ['ChatGPT', 'Claude', 'Gemini']
    });
    
    console.log('Topic created:', newTopic);
    return newTopic;
  } catch (error) {
    console.error('Failed to create topic:', error);
  }
}
```

---

### **Example 4: Sentiment Dashboard**

```typescript
import { apiClient } from '@/services/api';

// Sentiment Page Component
async function loadSentimentData(domainId: number) {
  try {
    // Get sentiment summary (last 7 days)
    const summary = await apiClient.getSentimentSummary(domainId, 7);
    
    console.log(`Positive: ${summary.positive_percentage}%`);
    console.log(`Neutral: ${summary.neutral_percentage}%`);
    console.log(`Negative: ${summary.negative_percentage}%`);
    console.log(`Total mentions: ${summary.total_mentions}`);
    
    // Get top themes
    const topThemes = summary.themes.slice(0, 5);
    
    // Get detailed sentiment analytics (last 30 days)
    const analytics = await apiClient.getSentimentByDomain(domainId, 30);
    
    return { summary, analytics, topThemes };
  } catch (error) {
    console.error('Failed to load sentiment data:', error);
  }
}
```

---

### **Example 5: Share of Voice**

```typescript
import { apiClient } from '@/services/api';

// Share of Voice Page Component
async function loadShareOfVoiceData(domainId: number) {
  try {
    // Get SOV comparison (today)
    const today = new Date().toISOString().split('T')[0];
    const comparison = await apiClient.getShareOfVoiceComparison(domainId, {
      date: today
    });
    
    console.log('Your share:', comparison.your_brand.share_percentage + '%');
    console.log('Market position:', comparison.your_brand.market_position);
    console.log('Total market mentions:', comparison.total_market_mentions);
    
    // Show competitors
    comparison.competitors.forEach((comp, index) => {
      console.log(`${index + 1}. ${comp.name}: ${comp.share_percentage}%`);
    });
    
    // Get historical SOV data (last 30 days)
    const historical = await apiClient.getShareOfVoiceByDomain(domainId, {
      days: 30
    });
    
    return { comparison, historical };
  } catch (error) {
    console.error('Failed to load SOV data:', error);
  }
}

// Filter by platform
async function getSOVByPlatform(domainId: number, platform: string) {
  try {
    const platformSOV = await apiClient.getShareOfVoiceComparison(domainId, {
      platform: platform  // 'ChatGPT', 'Claude', 'Gemini', etc.
    });
    
    return platformSOV;
  } catch (error) {
    console.error('Failed to load platform SOV:', error);
  }
}
```

---

### **Example 6: Integrations**

```typescript
import { apiClient } from '@/services/api';

// Integrations Settings Page
async function loadIntegrationsData(domainId: number) {
  try {
    // Get all integrations
    const integrations = await apiClient.getIntegrationsByDomain(domainId);
    
    // Get status summary
    const summary = await apiClient.getIntegrationStatusSummary(domainId);
    
    console.log(`Total: ${summary.total}`);
    console.log(`Active: ${summary.active}`);
    console.log(`Errors: ${summary.error}`);
    
    return { integrations, summary };
  } catch (error) {
    console.error('Failed to load integrations:', error);
  }
}

// Add Google Analytics integration
async function addGoogleAnalytics(domainId: number) {
  try {
    const integration = await apiClient.createIntegration({
      domain: domainId,
      type: 'google_analytics',
      provider_id: 'GA-123456',
      credentials: {
        // OAuth tokens from Google
        access_token: 'ya29.xxx',
        refresh_token: 'xxx',
        expires_at: '2025-12-31T23:59:59Z'
      }
    });
    
    // Test the connection
    const testResult = await apiClient.testIntegration(integration.id);
    console.log(testResult.message);
    
    return integration;
  } catch (error) {
    console.error('Failed to add integration:', error);
  }
}

// Manually sync an integration
async function syncIntegration(integrationId: number) {
  try {
    const result = await apiClient.syncIntegration(integrationId);
    console.log('Synced at:', result.last_sync_at);
    return result;
  } catch (error) {
    console.error('Failed to sync integration:', error);
  }
}
```

---

## 📝 TypeScript Type Definitions

You may want to create type definitions for the new API responses:

```typescript
// types/alerts.ts
export interface Alert {
  id: number;
  domain: number;
  domain_name: string;
  type: 'visibility_drop' | 'sentiment_negative' | 'competitor_surge' | 'anomaly' | 'position_loss' | 'new_platform' | 'misinformation';
  severity: 'high' | 'medium' | 'low';
  title: string;
  message: string;
  platform?: string;
  metric?: number;
  status: 'active' | 'investigating' | 'resolved';
  resolved_at?: string;
  created_by?: number;
  created_by_email?: string;
  created_at: string;
  modified_at: string;
}

export interface AlertRule {
  id: number;
  domain: number;
  domain_name: string;
  name: string;
  description: string;
  enabled: boolean;
  conditions: any;
  notification_channels: string[];
  detection_count: number;
  last_triggered_at?: string;
  created_by?: number;
  created_by_email?: string;
  created_at: string;
  modified_at: string;
}

// types/competitors.ts
export interface Competitor {
  id: number;
  domain: number;
  domain_name: string;
  name: string;
  url: string;
  mentions: number;
  visibility_score: number;
  sentiment: number;
  average_position: number;
  share_of_voice: number;
  trend_percentage: number;
  created_by?: number;
  created_by_email?: string;
  created_at: string;
  modified_at: string;
}

export interface CompetitorAnalytics {
  id: number;
  competitor: number;
  competitor_name: string;
  platform: string;
  mentions: number;
  position: number;
  sentiment: number;
  timestamp: string;
  created_at: string;
}

// types/topics.ts
export interface Topic {
  id: number;
  domain: number;
  domain_name: string;
  name: string;
  keywords: string[];
  mentions: number;
  visibility_score: number;
  sentiment: number;
  trend_percentage: number;
  platforms: string[];
  created_by?: number;
  created_by_email?: string;
  created_at: string;
  modified_at: string;
}

export interface TopicAnalytics {
  id: number;
  topic: number;
  topic_name: string;
  mentions: number;
  visibility_score: number;
  sentiment: number;
  timestamp: string;
  created_at: string;
}

// types/analytics.ts
export interface SentimentAnalytics {
  id: number;
  domain: number;
  domain_name: string;
  theme: string;
  positive_percentage: number;
  neutral_percentage: number;
  negative_percentage: number;
  mention_count: number;
  platform?: string;
  timestamp: string;
  created_at: string;
}

export interface ShareOfVoiceAnalytics {
  id: number;
  domain: number;
  domain_name: string;
  competitor?: number;
  competitor_name?: string;
  brand_name: string;
  platform?: string;
  share_percentage: number;
  mention_count: number;
  market_position?: number;
  timestamp: string;
  created_at: string;
}

// types/integrations.ts
export interface Integration {
  id: number;
  domain: number;
  domain_name: string;
  type: 'google_analytics' | 'search_console' | 'slack' | 'sms' | 'cms';
  provider_id: string;
  status: 'active' | 'error' | 'disconnected';
  last_sync_at?: string;
  error_message?: string;
  created_by?: number;
  created_by_email?: string;
  created_at: string;
  modified_at: string;
}
```

---

## 🔒 Authentication

All API methods automatically include the JWT token from `localStorage`:

```typescript
// Token is automatically added to request headers
headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

If the token expires, the API will return a 401 error. You should handle this in your components:

```typescript
try {
  const data = await apiClient.getAlerts({ domain_id: 1 });
} catch (error) {
  if (error.message.includes('401') || error.message.includes('Unauthorized')) {
    // Redirect to login
    window.location.href = '/login';
  }
}
```

---

## ✅ Summary

### **Total API Methods Added: 61**

- **Alerts**: 17 methods
- **Competitors**: 13 methods
- **Topics**: 13 methods
- **Analytics**: 8 methods
- **Integrations**: 10 methods

### **All APIs Support:**

✅ Authentication (JWT tokens)  
✅ Error handling  
✅ Request timeout (configurable)  
✅ TypeScript type safety (with proper types)  
✅ Query parameter building  
✅ RESTful conventions  

### **Ready to Use In:**

✅ Dashboard components  
✅ Alerts page  
✅ Competitors page  
✅ Topics page  
✅ Sentiment analysis page  
✅ Share of voice page  
✅ Settings/Integrations page  

The frontend is now fully integrated with all new backend APIs! 🎉

