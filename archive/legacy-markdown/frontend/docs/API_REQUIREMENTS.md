# AI Visibility Pro - Complete API & Integration Requirements

## Table of Contents
1. [Overview](#overview)
2. [Required APIs](#required-apis)
3. [OAuth Setup Instructions](#oauth-setup-instructions)
4. [Environment Variables](#environment-variables)
5. [Database Schema](#database-schema)
6. [Implementation Phases](#implementation-phases)
7. [Cost Estimation](#cost-estimation)
8. [Security Considerations](#security-considerations)

---

## Overview

This document details all external APIs, integrations, and dependencies required to build a fully functional AI Visibility Pro application.

**Application Purpose:**
Monitor brand mentions across AI platforms (ChatGPT, Claude, Gemini, Perplexity, Grok), track traffic attribution via Google Analytics and Search Console, detect misinformation, and generate comprehensive reports.

---

## Required APIs

### 1. AI Platform APIs (Core Functionality)

#### OpenAI API
**Purpose:** Monitor ChatGPT responses for brand mentions

**API Key:** `OPENAI_API_KEY`

**Setup:**
1. Create account at https://platform.openai.com/
2. Navigate to API Keys section
3. Generate new secret key
4. Store in Supabase Edge Function Secrets

**Models Used:**
- `gpt-5-2025-08-07` - Primary model for testing queries
- `gpt-5-mini-2025-08-07` - Cost-effective option

**API Endpoints:**
```
POST https://api.openai.com/v1/chat/completions
```

**Request Example:**
```typescript
const response = await fetch('https://api.openai.com/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${OPENAI_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'gpt-5-2025-08-07',
    messages: [
      { role: 'user', content: 'best vegan protein powder for athletes' }
    ],
    max_completion_tokens: 1000
  })
});
```

**Rate Limits:**
- Free tier: 3 RPM (requests per minute)
- Tier 1: 500 RPM
- Tier 5: 10,000 RPM

**Pricing:**
- GPT-5: $2.50 per 1M input tokens, $10 per 1M output tokens
- GPT-5-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens

**Estimated Monthly Cost:** $100-300 (depends on query volume)

---

#### Anthropic API (Claude)
**Purpose:** Monitor Claude responses for brand mentions

**API Key:** `ANTHROPIC_API_KEY`

**Setup:**
1. Create account at https://console.anthropic.com/
2. Navigate to API Keys
3. Generate new key
4. Store in Supabase secrets

**Models Used:**
- `claude-sonnet-4-5` - Most capable model
- `claude-opus-4-1-20250805` - Alternative high-intelligence model

**API Endpoints:**
```
POST https://api.anthropic.com/v1/messages
```

**Request Example:**
```typescript
const response = await fetch('https://api.anthropic.com/v1/messages', {
  method: 'POST',
  headers: {
    'x-api-key': ANTHROPIC_API_KEY,
    'anthropic-version': '2023-06-01',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'claude-sonnet-4-5',
    max_tokens: 1024,
    messages: [
      { role: 'user', content: 'best vegan protein powder for athletes' }
    ]
  })
});
```

**Rate Limits:**
- Tier 1: 50 RPM, 40,000 TPM (tokens per minute)
- Tier 4: 4,000 RPM, 400,000 TPM

**Pricing:**
- Claude Sonnet 4.5: $3 per 1M input tokens, $15 per 1M output tokens
- Claude Opus 4.1: $15 per 1M input tokens, $75 per 1M output tokens

**Estimated Monthly Cost:** $150-400

---

#### Google Gemini API
**Purpose:** Monitor Gemini responses for brand mentions

**API Key:** `GOOGLE_GEMINI_API_KEY`

**Setup:**
1. Create project at https://console.cloud.google.com/
2. Enable Generative Language API
3. Create API credentials
4. Store in Supabase secrets

**Models Used:**
- `gemini-2.5-pro` - Flagship model
- `gemini-2.5-flash` - Faster, cost-effective

**API Endpoints:**
```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
```

**Request Example:**
```typescript
const response = await fetch(
  `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GOOGLE_GEMINI_API_KEY}`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{
        parts: [{
          text: 'best vegan protein powder for athletes'
        }]
      }]
    })
  }
);
```

**Rate Limits:**
- Free tier: 15 RPM
- Paid: 1,000 RPM

**Pricing:**
- Gemini 2.5 Pro: $1.25 per 1M input tokens, $5 per 1M output tokens
- Gemini 2.5 Flash: $0.075 per 1M input tokens, $0.30 per 1M output tokens

**Estimated Monthly Cost:** $50-150

---

#### Perplexity API
**Purpose:** Monitor Perplexity AI responses for brand mentions

**API Key:** `PERPLEXITY_API_KEY`

**Setup:**
1. Create account at https://www.perplexity.ai/
2. Navigate to API settings
3. Generate API key
4. Store in Supabase secrets

**Models Used:**
- `llama-3.1-sonar-large-128k-online` - Primary online model
- `llama-3.1-sonar-small-128k-online` - Cost-effective option

**API Endpoints:**
```
POST https://api.perplexity.ai/chat/completions
```

**Request Example:**
```typescript
const response = await fetch('https://api.perplexity.ai/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${PERPLEXITY_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'llama-3.1-sonar-large-128k-online',
    messages: [
      { role: 'user', content: 'best vegan protein powder for athletes' }
    ],
    temperature: 0.2,
    return_citations: true
  })
});
```

**Rate Limits:**
- Standard: 50 RPM
- Pro: 1,000 RPM

**Pricing:**
- Sonar Small: $0.20 per 1M tokens
- Sonar Large: $1.00 per 1M tokens

**Estimated Monthly Cost:** $30-100

---

#### X.AI API (Grok)
**Purpose:** Monitor Grok responses for brand mentions

**API Key:** `XAI_API_KEY`

**Setup:**
1. Create account at https://x.ai/
2. Request API access
3. Generate API key
4. Store in Supabase secrets

**Models Used:**
- `grok-2` - Latest Grok model

**API Endpoints:**
```
POST https://api.x.ai/v1/chat/completions
```

**Request Example:**
```typescript
const response = await fetch('https://api.x.ai/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${XAI_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'grok-2',
    messages: [
      { role: 'user', content: 'best vegan protein powder for athletes' }
    ]
  })
});
```

**Rate Limits:** TBD (API in beta)

**Pricing:** TBD

**Estimated Monthly Cost:** $50-150 (estimated)

---

### 2. Analytics & Traffic Attribution APIs

#### Google Analytics API (GA4)
**Purpose:** Track website traffic from AI platforms

**Authentication:** OAuth 2.0 (per domain)

**Setup:**
1. Create project at https://console.cloud.google.com/
2. Enable APIs:
   - Google Analytics Data API
   - Google Analytics Admin API
3. Create OAuth 2.0 Client ID:
   - Application type: Web application
   - Authorized JavaScript origins: `https://your-app.lovable.app`
   - Authorized redirect URIs: `https://your-app.lovable.app/auth/google/callback`
4. Download credentials JSON

**Required OAuth Scopes:**
```
https://www.googleapis.com/auth/analytics.readonly
```

**API Endpoints:**
```
POST https://analyticsdata.googleapis.com/v1beta/properties/{propertyId}:runReport
```

**Request Example:**
```typescript
const response = await fetch(
  `https://analyticsdata.googleapis.com/v1beta/properties/${GA_PROPERTY_ID}:runReport`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      dateRanges: [{ startDate: '7daysAgo', endDate: 'today' }],
      dimensions: [
        { name: 'sessionSource' },
        { name: 'sessionMedium' }
      ],
      metrics: [
        { name: 'sessions' },
        { name: 'conversions' },
        { name: 'totalRevenue' }
      ],
      dimensionFilter: {
        filter: {
          fieldName: 'sessionSource',
          inListFilter: {
            values: ['chat.openai.com', 'claude.ai', 'gemini.google.com']
          }
        }
      }
    })
  }
);
```

**Data Points Collected:**
- Sessions by source/medium
- Page views
- Bounce rate
- Average session duration
- Goal completions
- E-commerce conversions
- Revenue
- Device breakdown
- Geographic data

**Rate Limits:**
- 100 requests per 100 seconds per project
- 10 concurrent requests

**Pricing:** Free (within quotas)

**Storage:**
- OAuth tokens stored per domain in `integrations` table
- Access token (1 hour expiry)
- Refresh token (long-lived)

---

#### Google Search Console API
**Purpose:** Track search queries leading to AI mentions

**Authentication:** OAuth 2.0 (per domain)

**Setup:**
1. Use same Google Cloud project as GA
2. Enable Google Search Console API
3. Use same OAuth credentials
4. Domain must be verified in Search Console

**Required OAuth Scopes:**
```
https://www.googleapis.com/auth/webmasters.readonly
```

**API Endpoints:**
```
POST https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/searchAnalytics/query
```

**Request Example:**
```typescript
const response = await fetch(
  `https://www.googleapis.com/webmasters/v3/sites/${encodeURIComponent(siteUrl)}/searchAnalytics/query`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      startDate: '2025-01-01',
      endDate: '2025-01-31',
      dimensions: ['query', 'page'],
      rowLimit: 1000
    })
  }
);
```

**Data Points Collected:**
- Search queries
- Impressions
- Clicks
- CTR (click-through rate)
- Average position
- Top pages

**Rate Limits:**
- 1,200 queries per minute per project
- 100 queries per second per project

**Pricing:** Free

---

### 3. Content Analysis & Verification

#### Firecrawl API
**Purpose:** Scrape website content for comparison with AI responses

**API Key:** `FIRECRAWL_API_KEY`

**Setup:**
1. Sign up at https://firecrawl.dev/
2. Navigate to API Keys section
3. Generate new key
4. Store in Supabase secrets

**API Endpoints:**
```
POST https://api.firecrawl.dev/v0/crawl
GET https://api.firecrawl.dev/v0/crawl/{jobId}
```

**Request Example:**
```typescript
// Start crawl
const crawlResponse = await fetch('https://api.firecrawl.dev/v0/crawl', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${FIRECRAWL_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://example.com/product',
    limit: 5,
    scrapeOptions: {
      formats: ['markdown', 'html']
    }
  })
});

// Check status
const statusResponse = await fetch(
  `https://api.firecrawl.dev/v0/crawl/${jobId}`,
  {
    headers: { 'Authorization': `Bearer ${FIRECRAWL_API_KEY}` }
  }
);
```

**Use Cases:**
1. Scrape product pages cited by AI
2. Extract current pricing and specifications
3. Verify company information
4. Compare against AI-generated content

**Rate Limits:**
- Starter: 500 credits/month
- Growth: 5,000 credits/month
- 1 credit = 1 page scraped

**Pricing:**
- Starter: Free (500 pages/month)
- Growth: $19/month (5,000 pages)
- Scale: Custom pricing

**Estimated Monthly Cost:** $19-49

---

#### Lovable AI Gateway
**Purpose:** Semantic comparison of content for misinformation detection

**API Key:** `LOVABLE_API_KEY` (auto-provisioned)

**Setup:** Already configured in Lovable Cloud

**Models Available:**
- `google/gemini-2.5-flash` - Recommended for content comparison
- `google/gemini-2.5-pro` - Higher accuracy
- `openai/gpt-5-mini` - Alternative option

**API Endpoints:**
```
POST https://ai.gateway.lovable.dev/v1/chat/completions
```

**Request Example:**
```typescript
const response = await fetch('https://ai.gateway.lovable.dev/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${LOVABLE_API_KEY}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: 'google/gemini-2.5-flash',
    messages: [
      {
        role: 'system',
        content: 'Compare the following AI response with the original website content and identify any factual inaccuracies.'
      },
      {
        role: 'user',
        content: `
AI Response: ${aiResponse}

Original Content: ${websiteContent}

Analyze and return:
1. Factual accuracy (true/false)
2. Specific inaccuracies found
3. Severity (high/medium/low)
        `
      }
    ]
  })
});
```

**Rate Limits:**
- Subject to workspace limits
- 429 error if rate limit exceeded
- 402 error if credits exhausted

**Pricing:**
- Included usage per workspace
- Overage charged based on model
- Check https://docs.lovable.dev/features/ai for current rates

**Estimated Monthly Cost:** $20-100 (within included usage + potential overage)

---

### 4. Notifications & Alerts

#### Resend Email API
**Purpose:** Send email notifications for alerts and reports

**API Key:** `RESEND_API_KEY`

**Setup:**
1. Sign up at https://resend.com/
2. Verify email domain at https://resend.com/domains
3. Create API key at https://resend.com/api-keys
4. Store in Supabase secrets

**API Endpoints:**
```
POST https://api.resend.com/emails
```

**Request Example:**
```typescript
import { Resend } from 'npm:resend@2.0.0';

const resend = new Resend(Deno.env.get('RESEND_API_KEY'));

const emailResponse = await resend.emails.send({
  from: 'AI Visibility Pro <alerts@yourdomain.com>',
  to: ['user@example.com'],
  subject: 'New Misinformation Alert Detected',
  html: `
    <h1>Misinformation Alert</h1>
    <p>Platform: ChatGPT</p>
    <p>Severity: High</p>
    <p>Issue: Incorrect pricing information</p>
    <a href="https://app.yourdomain.com/alerts/123">View Details</a>
  `
});
```

**Use Cases:**
- Misinformation alerts
- Weekly summary reports
- Report generation completion
- Team member invitations
- Password reset emails

**Rate Limits:**
- Free: 100 emails/day
- Pro: 50,000 emails/month

**Pricing:**
- Free: 100 emails/day, 3,000/month
- Pro: $20/month (50,000 emails)

**Estimated Monthly Cost:** $0-20

---

#### Slack Webhooks (Optional)
**Purpose:** Real-time alert notifications to Slack channels

**Webhook URL:** User-provided per organization

**Setup:**
1. User creates Slack app or incoming webhook
2. User provides webhook URL in Organization Settings
3. Store webhook URL in database per organization

**API Endpoints:**
```
POST {user_provided_webhook_url}
```

**Request Example:**
```typescript
await fetch(slackWebhookUrl, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: '🚨 New Misinformation Alert',
    blocks: [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: '🚨 Misinformation Detected'
        }
      },
      {
        type: 'section',
        fields: [
          { type: 'mrkdwn', text: `*Platform:*\nChatGPT` },
          { type: 'mrkdwn', text: `*Severity:*\nHigh` },
          { type: 'mrkdwn', text: `*Issue:*\nIncorrect pricing` }
        ]
      },
      {
        type: 'actions',
        elements: [
          {
            type: 'button',
            text: { type: 'plain_text', text: 'View Details' },
            url: 'https://app.yourdomain.com/alerts/123'
          }
        ]
      }
    ]
  })
});
```

**Rate Limits:** 1 message per second per webhook

**Pricing:** Free (user's Slack workspace)

---

### 5. Authentication & Database

#### Supabase (Lovable Cloud)
**Purpose:** Authentication, database, storage, edge functions

**Keys:** Auto-provisioned
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

**Features Used:**
- **Supabase Auth:**
  - Email/password authentication
  - Session management
  - Optional Google OAuth
  
- **PostgreSQL Database:**
  - Organizations, domains, mentions
  - Integrations, alerts, rules
  - Traffic attribution data
  - Row-Level Security (RLS) policies
  
- **Edge Functions:**
  - AI crawler jobs
  - OAuth token exchange
  - Report generation
  - Email sending
  - Webhook handlers
  
- **Storage:**
  - Generated PDF reports
  - Screenshots (optional)
  - Export files

**Pricing:**
- Free tier: Included with Lovable
- Overage: Based on usage
- Database: First 500MB free, then $0.125/GB
- Storage: First 1GB free, then $0.021/GB
- Edge Functions: First 500k invocations free

**Estimated Monthly Cost:** $0-50 (within free tier for most use cases)

---

## OAuth Setup Instructions

### Google OAuth Configuration

**Step 1: Create Google Cloud Project**

1. Go to https://console.cloud.google.com/
2. Click "Select a project" → "New Project"
3. Enter project name: "AI Visibility Pro"
4. Click "Create"

**Step 2: Enable Required APIs**

1. Navigate to "APIs & Services" → "Library"
2. Search and enable the following APIs:
   - Google Analytics Data API
   - Google Analytics Admin API
   - Google Search Console API

**Step 3: Configure OAuth Consent Screen**

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type
3. Fill in application details:
   - App name: AI Visibility Pro
   - User support email: your-email@domain.com
   - Developer contact: your-email@domain.com
4. Add scopes:
   - `https://www.googleapis.com/auth/analytics.readonly`
   - `https://www.googleapis.com/auth/webmasters.readonly`
5. Add test users (during development)
6. Click "Save and Continue"

**Step 4: Create OAuth 2.0 Credentials**

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Web application"
4. Name: "AI Visibility Pro Web Client"
5. Authorized JavaScript origins:
   ```
   https://your-app.lovable.app
   https://your-custom-domain.com
   http://localhost:5173 (for development)
   ```
6. Authorized redirect URIs:
   ```
   https://your-app.lovable.app/auth/google/callback
   https://your-custom-domain.com/auth/google/callback
   http://localhost:5173/auth/google/callback
   ```
7. Click "Create"
8. Download JSON credentials
9. Extract Client ID and Client Secret

**Step 5: Store Credentials**

Store in Supabase Edge Function Secrets:
```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
```

**Step 6: Implement OAuth Flow**

See architecture documentation for detailed OAuth sequence diagram.

**Token Storage Schema:**
```sql
CREATE TABLE integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_id UUID REFERENCES domains(id),
  type TEXT CHECK (type IN ('google_analytics', 'search_console')),
  property_id TEXT, -- GA4 property ID or GSC site URL
  oauth_tokens JSONB, -- Encrypted
  status TEXT CHECK (status IN ('active', 'error', 'expired')),
  last_sync TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Token Refresh Logic:**
```typescript
async function refreshAccessToken(refreshToken: string) {
  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: GOOGLE_OAUTH_CLIENT_ID,
      client_secret: GOOGLE_OAUTH_CLIENT_SECRET,
      refresh_token: refreshToken,
      grant_type: 'refresh_token'
    })
  });
  
  const { access_token, expires_in } = await response.json();
  
  return {
    accessToken: access_token,
    expiresAt: Date.now() + (expires_in * 1000)
  };
}
```

---

## Environment Variables

### Supabase Edge Function Secrets

Store all API keys as Supabase secrets (encrypted at rest):

```bash
# AI Platform APIs
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_GEMINI_API_KEY=AIza...
PERPLEXITY_API_KEY=pplx-...
XAI_API_KEY=xai-...

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...

# Content Analysis
FIRECRAWL_API_KEY=fc-...

# Notifications
RESEND_API_KEY=re_...

# Auto-provisioned (don't set manually)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
LOVABLE_API_KEY=lvbl-...
```

### Frontend Environment Variables (.env)

Auto-configured by Lovable:
```bash
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJhbGc...
VITE_SUPABASE_PROJECT_ID=xxx
```

---

## Database Schema

See `ARCHITECTURE_FLOWS.md` for complete ERD diagram.

### Core Tables:

```sql
-- Organizations (tenants)
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Domains tracked per organization
CREATE TABLE domains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  domain TEXT NOT NULL,
  verified BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, domain)
);

-- Google Analytics & Search Console integrations
CREATE TABLE integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
  type TEXT CHECK (type IN ('google_analytics', 'search_console')),
  property_id TEXT, -- GA4 property ID
  property_url TEXT, -- GSC site URL
  oauth_tokens JSONB NOT NULL, -- { access_token, refresh_token, expires_at }
  status TEXT CHECK (status IN ('active', 'error', 'expired')) DEFAULT 'active',
  last_sync TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(domain_id, type)
);

-- AI platform mentions
CREATE TABLE mentions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
  platform TEXT CHECK (platform IN ('chatgpt', 'claude', 'gemini', 'perplexity', 'grok')),
  prompt TEXT NOT NULL,
  response TEXT NOT NULL,
  position INTEGER,
  sentiment TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative')),
  url TEXT,
  detected_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Citations extracted from mentions
CREATE TABLE citations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mention_id UUID REFERENCES mentions(id) ON DELETE CASCADE,
  quoted_text TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_name TEXT NOT NULL,
  context TEXT,
  reliability TEXT CHECK (reliability IN ('high', 'medium', 'low')) DEFAULT 'medium',
  timestamp TIMESTAMPTZ DEFAULT now()
);

-- Misinformation alerts
CREATE TABLE misinformation_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mention_id UUID REFERENCES mentions(id) ON DELETE SET NULL,
  rule_id UUID REFERENCES monitoring_rules(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT CHECK (severity IN ('high', 'medium', 'low')),
  status TEXT CHECK (status IN ('investigating', 'correcting', 'escalated', 'monitoring', 'verified')) DEFAULT 'investigating',
  platform TEXT,
  correct_info TEXT,
  incorrect_info TEXT,
  impact_category TEXT,
  affected_mentions INTEGER DEFAULT 1,
  detected_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Monitoring rules
CREATE TABLE monitoring_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT CHECK (status IN ('active', 'paused')) DEFAULT 'active',
  conditions JSONB NOT NULL,
  actions JSONB NOT NULL,
  detections_count INTEGER DEFAULT 0,
  last_triggered TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Team members
CREATE TABLE team_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT CHECK (role IN ('admin', 'user')) DEFAULT 'user',
  joined_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(org_id, user_id)
);

-- Traffic attribution (aggregated daily)
CREATE TABLE traffic_attribution (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_id UUID REFERENCES domains(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  source TEXT NOT NULL, -- 'chatgpt', 'claude', etc.
  sessions INTEGER DEFAULT 0,
  page_views INTEGER DEFAULT 0,
  bounce_rate NUMERIC(5,2),
  avg_duration NUMERIC(10,2), -- seconds
  conversions INTEGER DEFAULT 0,
  revenue NUMERIC(10,2),
  device_breakdown JSONB, -- { desktop: 100, mobile: 50, tablet: 10 }
  geo_breakdown JSONB, -- { US: 80, UK: 30, ... }
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(domain_id, date, source)
);
```

### Row-Level Security Policies:

```sql
-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentions ENABLE ROW LEVEL SECURITY;
ALTER TABLE citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE misinformation_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitoring_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE traffic_attribution ENABLE ROW LEVEL SECURITY;

-- Example: Users can only access their organization's data
CREATE POLICY "Users access own org domains"
ON domains FOR SELECT
USING (
  org_id IN (
    SELECT org_id FROM team_members
    WHERE user_id = auth.uid()
  )
);

CREATE POLICY "Users access own org mentions"
ON mentions FOR SELECT
USING (
  domain_id IN (
    SELECT d.id FROM domains d
    JOIN team_members tm ON tm.org_id = d.org_id
    WHERE tm.user_id = auth.uid()
  )
);

-- Only admins can manage integrations
CREATE POLICY "Admins manage integrations"
ON integrations FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM domains d
    JOIN team_members tm ON tm.org_id = d.org_id
    WHERE d.id = integrations.domain_id
    AND tm.user_id = auth.uid()
    AND tm.role = 'admin'
  )
);
```

---

## Implementation Phases

### Phase 1: Core Monitoring (Weeks 1-3)
**Goal:** Get basic mention tracking working

**Tasks:**
1. ✅ Set up Supabase database schema
2. ✅ Create organizations, domains, mentions tables
3. ✅ Implement authentication (email/password)
4. ✅ Set up RLS policies
5. 🔨 Add API keys for AI platforms (OpenAI, Anthropic, Google, Perplexity, XAI)
6. 🔨 Create Edge Function: `crawl-ai-platforms`
   - Accept prompt and platform list
   - Call each AI API
   - Parse responses for mentions
   - Store in database
7. 🔨 Build frontend:
   - Dashboard with metrics
   - Mentions list page
   - Mention detail page
   - Organization settings
8. 🔨 Implement scheduled crawler (cron job)
9. ✅ Deploy and test

**Deliverables:**
- Working dashboard showing AI mentions
- Manual and scheduled crawling
- Basic search and filtering

---

### Phase 2: Traffic Attribution (Weeks 4-6)
**Goal:** Connect Google Analytics and Search Console

**Tasks:**
1. 🔨 Set up Google Cloud Project
2. 🔨 Enable GA and GSC APIs
3. 🔨 Configure OAuth consent screen
4. 🔨 Create OAuth credentials
5. 🔨 Build OAuth flow:
   - Edge Function: `google-oauth-init`
   - Edge Function: `google-oauth-callback`
   - Store tokens per domain
6. 🔨 Create integrations management UI
   - Connect/disconnect buttons
   - Token status display
   - Error handling
7. 🔨 Build data sync Edge Function: `sync-analytics`
   - Fetch GA data (sessions, conversions, revenue)
   - Fetch GSC data (queries, impressions, clicks)
   - Store in traffic_attribution table
   - Run daily via cron
8. 🔨 Build Traffic Attribution dashboard:
   - Traffic sources breakdown
   - Conversion paths
   - ROI calculation
   - Device and geo data
9. ✅ Deploy and test

**Deliverables:**
- Google OAuth integration working
- Daily analytics sync
- Traffic attribution dashboard

---

### Phase 3: Misinformation Detection (Weeks 7-9)
**Goal:** Identify and alert on hallucinations

**Tasks:**
1. 🔨 Add Firecrawl API integration
2. 🔨 Create Edge Function: `verify-content`
   - Accept mention ID
   - Extract citations from mention
   - Scrape original source via Firecrawl
   - Compare using Lovable AI
   - Return accuracy score and discrepancies
3. 🔨 Build monitoring rules system:
   - Create/edit rules UI
   - Define conditions (keywords, severity thresholds)
   - Define actions (alert channels)
4. 🔨 Create Edge Function: `check-misinformation`
   - Run after each mention is stored
   - Apply monitoring rules
   - Create alerts if rules match
   - Trigger notifications
5. 🔨 Build alert notification system:
   - Edge Function: `send-alert-email` (Resend)
   - Edge Function: `send-alert-slack` (webhooks)
   - Queue system for batching
6. 🔨 Build Misinformation Alerts page:
   - Active cases list
   - Resolved cases history
   - Alert detail view
   - Action tracking (investigate → correct → verify)
7. 🔨 Implement Content Comparison UI
   - Side-by-side comparison
   - Highlight differences
   - Manual verification option
8. ✅ Deploy and test

**Deliverables:**
- Automated misinformation detection
- Email and Slack alerts
- Alert management dashboard

---

### Phase 4: Reports & Automation (Weeks 10-12)
**Goal:** Generate PDF reports and automate workflows

**Tasks:**
1. 🔨 Build report templates (HTML):
   - Executive Summary
   - Detailed Analytics
   - Misinformation Report
   - Traffic Attribution Report
2. 🔨 Create Edge Function: `generate-report`
   - Accept report type and parameters
   - Fetch data from database
   - Render HTML template
   - Convert to PDF using Puppeteer
   - Upload to Supabase Storage
   - Return download URL
3. 🔨 Build Reports page:
   - Report history
   - Generate new report UI
   - Schedule recurring reports
   - Download/email options
4. 🔨 Implement scheduled reports:
   - Cron job: `scheduled-reports`
   - Check for scheduled reports
   - Generate and email
5. 🔨 Add export functionality:
   - CSV exports for mentions
   - CSV exports for analytics
   - API access for integrations
6. 🔨 Build API documentation page
7. ✅ Deploy and test

**Deliverables:**
- PDF report generation
- Scheduled weekly/monthly reports
- CSV exports
- API access

---

### Phase 5: Polish & Optimization (Week 13+)
**Goal:** Production-ready application

**Tasks:**
1. 🔨 Performance optimization:
   - Database indexing
   - Query optimization
   - Edge Function caching
   - Frontend code splitting
2. 🔨 Error handling improvements
3. 🔨 Loading states and skeletons
4. 🔨 Empty states and onboarding
5. 🔨 Mobile responsiveness
6. 🔨 Accessibility (WCAG AA)
7. 🔨 SEO optimization
8. 🔨 Analytics and monitoring:
   - Error tracking (Sentry)
   - Usage analytics (PostHog)
9. 🔨 Documentation:
   - User guide
   - API documentation
   - Video tutorials
10. ✅ Production deployment

**Deliverables:**
- Production-ready application
- Complete documentation
- Monitoring and analytics

---

## Cost Estimation

### Monthly Costs (Estimated)

**AI Platform APIs:**
- OpenAI: $100-300
- Anthropic: $150-400
- Google Gemini: $50-150
- Perplexity: $30-100
- X.AI: $50-150
**Subtotal:** $380-1,100/month

**Content Analysis:**
- Firecrawl: $19-49/month
- Lovable AI: $20-100/month
**Subtotal:** $39-149/month

**Notifications:**
- Resend: $0-20/month
- Slack: Free
**Subtotal:** $0-20/month

**Infrastructure:**
- Supabase/Lovable Cloud: $0-50/month
- Google APIs: Free
**Subtotal:** $0-50/month

**Total Monthly Cost:** $419-1,319/month

**Per Customer:**
Assuming 100 customers: $4.19-13.19 per customer
Assuming 500 customers: $0.84-2.64 per customer

**Cost Optimization Strategies:**
1. Use cheaper models for initial crawls (GPT-5-mini, Gemini Flash)
2. Cache AI responses to avoid duplicate queries
3. Batch API requests where possible
4. Use Lovable AI for most content comparisons (included usage)
5. Implement rate limiting to prevent abuse
6. Start with limited platforms, add more based on demand

---

## Security Considerations

### API Key Management:
- ✅ Store all keys in Supabase Edge Function Secrets (encrypted at rest)
- ✅ Never expose keys in frontend code
- ✅ Use environment variables in Edge Functions
- ✅ Rotate keys quarterly
- ✅ Implement key usage monitoring

### OAuth Token Security:
- ✅ Store tokens encrypted in database
- ✅ Use Row-Level Security (RLS) to restrict access
- ✅ Implement token refresh logic
- ✅ Handle token expiry gracefully
- ✅ Log OAuth errors for debugging

### Database Security:
- ✅ Enable RLS on all tables
- ✅ Create policies for multi-tenant isolation
- ✅ Use prepared statements (prevent SQL injection)
- ✅ Implement rate limiting on Edge Functions
- ✅ Regular database backups

### Authentication Security:
- ✅ Enforce strong password requirements
- ✅ Implement email verification
- ✅ Use secure session management (Supabase Auth)
- ✅ Optional 2FA for admin accounts
- ✅ Log all authentication attempts

### Data Privacy:
- ✅ GDPR compliance (data deletion on request)
- ✅ Encrypt sensitive data at rest
- ✅ Use HTTPS for all communications
- ✅ Implement audit logs for admin actions
- ✅ Regular security audits

### Rate Limiting:
- ✅ Implement per-user rate limits
- ✅ Implement per-organization rate limits
- ✅ Prevent API abuse with exponential backoff
- ✅ Monitor unusual activity patterns

---

## Appendix

### Useful Resources:

**API Documentation:**
- OpenAI: https://platform.openai.com/docs/
- Anthropic: https://docs.anthropic.com/
- Google Gemini: https://ai.google.dev/docs
- Perplexity: https://docs.perplexity.ai/
- Google Analytics: https://developers.google.com/analytics/devguides/reporting/data/v1
- Google Search Console: https://developers.google.com/webmaster-tools/search-console-api-original
- Firecrawl: https://docs.firecrawl.dev/
- Resend: https://resend.com/docs
- Lovable AI: https://docs.lovable.dev/features/ai

**Supabase Resources:**
- Supabase Docs: https://supabase.com/docs
- Edge Functions: https://supabase.com/docs/guides/functions
- Row-Level Security: https://supabase.com/docs/guides/auth/row-level-security
- Realtime: https://supabase.com/docs/guides/realtime

**Development Tools:**
- Lovable Docs: https://docs.lovable.dev/
- React Query: https://tanstack.com/query/latest
- Shadcn/ui: https://ui.shadcn.com/
- Tailwind CSS: https://tailwindcss.com/

### Support Contacts:
- Lovable Support: support@lovable.dev
- Community Discord: https://discord.com/channels/1119885301872070706

---

**Document Version:** 1.0
**Last Updated:** 2025-01-15
**Author:** AI Visibility Pro Development Team
