# Frontend API Integration Guide

## ✅ Status: Seed Data Loaded & APIs Ready

### Database Status
✅ **10 Organizations created**  
✅ **10 Users with permissions**  
✅ **600+ records across all tables**  
✅ **All API endpoints functional**

### Login Credentials
**Superadmin:**
- Email: `admin@llmmonitor.com`
- Password: `Admin@123`

**Test Users:**
- Email: `user1@techcorpsolutions.com` through `user9@fitnesspro.com`
- Password: `User@123`

---

## 🚀 Quick Start

### 1. Environment Setup

Create `/frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
```

### 2. API Service Layer Created

✅ **Created Files:**
- `/frontend/src/services/api.ts` - Base API client
- `/frontend/src/services/auth.service.ts` - Authentication services
- `/frontend/src/services/index.ts` - Service exports

---

## 📱 Page Integration Examples

### Dashboard (`/`)

**API Endpoints Needed:**
```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services';

function Dashboard() {
  // Fetch domains
  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: () => api.get('/domains/')
  });

  // Fetch mentions summary
  const { data: mentions } = useQuery({
    queryKey: ['mentions-summary'],
    queryFn: () => api.get('/prompts/mentions/?days=30')
  });

  // Fetch sentiment analytics
  const { data: sentiment } = useQuery({
    queryKey: ['sentiment-analytics'],
    queryFn: () => api.get('/analytics/sentiment-analytics/?timestamp__gte=2025-10-01')
  });

  // Fetch share of voice
  const { data: shareOfVoice } = useQuery({
    queryKey: ['share-of-voice'],
    queryFn: () => api.get('/analytics/share-of-voice/?timestamp__gte=2025-10-01')
  });

  // Fetch active alerts
  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.get('/alerts/alerts/?status=active')
  });

  return (
    <div>
      {/* Render your dashboard with the data */}
    </div>
  );
}
```

---

### Mentions (`/mentions`)

**Complete Integration:**
```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/services';

interface MentionFilters {
  platform?: string;
  sentiment?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
}

function Mentions() {
  const [filters, setFilters] = useState<MentionFilters>({});

  // Fetch mentions with filters
  const { data: mentions, isLoading } = useQuery({
    queryKey: ['mentions', filters],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.platform) params.append('platform', filters.platform);
      if (filters.sentiment) params.append('sentiment', filters.sentiment);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);
      if (filters.page) params.append('page', filters.page.toString());
      
      return api.get(`/prompts/mentions/?${params.toString()}`);
    }
  });

  // Get filter options
  const { data: filterOptions } = useQuery({
    queryKey: ['mention-filters'],
    queryFn: () => api.get('/prompts/mentions/filters/')
  });

  // Export mentions mutation
  const exportMutation = useMutation({
    mutationFn: (exportData: any) =>
      api.post('/prompts/mentions/export/', exportData),
    onSuccess: (data) => {
      // Handle export success (download file, etc.)
      console.log('Export successful', data);
    }
  });

  return (
    <div>
      {/* Filter UI */}
      {/* Mentions Table */}
      {/* Pagination */}
    </div>
  );
}
```

---

### Prompts (`/prompts`)

```typescript
function Prompts() {
  // Fetch prompt groups
  const { data: groups } = useQuery({
    queryKey: ['prompt-groups'],
    queryFn: () => api.get('/prompts/groups/')
  });

  // Fetch prompts
  const { data: prompts } = useQuery({
    queryKey: ['prompts'],
    queryFn: () => api.get('/prompts/prompts/')
  });

  // Create prompt group mutation
  const createGroupMutation = useMutation({
    mutationFn: (newGroup: any) =>
      api.post('/prompts/groups/', newGroup),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt-groups'] });
    }
  });

  // Create prompt mutation
  const createPromptMutation = useMutation({
    mutationFn: (newPrompt: any) =>
      api.post('/prompts/prompts/', newPrompt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    }
  });

  return <div>{/* Your prompts UI */}</div>;
}
```

---

### Alerts (`/alerts`)

```typescript
function Alerts() {
  // Fetch alerts
  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.get('/alerts/alerts/')
  });

  // Fetch alert rules
  const { data: alertRules } = useQuery({
    queryKey: ['alert-rules'],
    queryFn: () => api.get('/alerts/alert-rules/')
  });

  // Create alert rule mutation
  const createRuleMutation = useMutation({
    mutationFn: (newRule: any) =>
      api.post('/alerts/alert-rules/', newRule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-rules'] });
    }
  });

  // Update alert status mutation
  const updateAlertMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.patch(`/alerts/alerts/${id}/`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    }
  });

  return <div>{/* Your alerts UI */}</div>;
}
```

---

### Sentiment Analysis (`/sentiment`)

```typescript
function Sentiment() {
  const [dateRange, setDateRange] = useState({
    start: subDays(new Date(), 30),
    end: new Date()
  });

  // Fetch sentiment data
  const { data: sentimentData } = useQuery({
    queryKey: ['sentiment', dateRange],
    queryFn: () => api.get(
      `/analytics/sentiment-analytics/?` +
      `timestamp__gte=${format(dateRange.start, 'yyyy-MM-dd')}&` +
      `timestamp__lte=${format(dateRange.end, 'yyyy-MM-dd')}`
    )
  });

  return (
    <div>
      <DateRangePicker value={dateRange} onChange={setDateRange} />
      {/* Sentiment charts and visualizations */}
    </div>
  );
}
```

---

### Topics (`/topics`)

```typescript
function Topics() {
  // Fetch topics
  const { data: topics } = useQuery({
    queryKey: ['topics'],
    queryFn: () => api.get('/topics/topics/')
  });

  // Fetch topic analytics
  const { data: topicAnalytics } = useQuery({
    queryKey: ['topic-analytics'],
    queryFn: () => api.get('/topics/topic-analytics/')
  });

  // Create topic mutation
  const createTopicMutation = useMutation({
    mutationFn: (newTopic: any) =>
      api.post('/topics/topics/', newTopic),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topics'] });
    }
  });

  return <div>{/* Your topics UI */}</div>;
}
```

---

### Share of Voice (`/share-of-voice`)

```typescript
function ShareOfVoice() {
  const [timeRange, setTimeRange] = useState('30d');

  // Fetch share of voice data
  const { data: sovData } = useQuery({
    queryKey: ['share-of-voice', timeRange],
    queryFn: () => {
      const daysAgo = timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 7;
      const startDate = format(subDays(new Date(), daysAgo), 'yyyy-MM-dd');
      
      return api.get(
        `/analytics/share-of-voice/?timestamp__gte=${startDate}`
      );
    }
  });

  // Fetch competitors for comparison
  const { data: competitors } = useQuery({
    queryKey: ['competitors'],
    queryFn: () => api.get('/competitors/competitors/')
  });

  return <div>{/* SOV charts and analysis */}</div>;
}
```

---

### Competitors (`/competitors`)

```typescript
function Competitors() {
  // Fetch competitors
  const { data: competitors } = useQuery({
    queryKey: ['competitors'],
    queryFn: () => api.get('/competitors/competitors/')
  });

  // Create competitor mutation
  const createCompetitorMutation = useMutation({
    mutationFn: (newCompetitor: any) =>
      api.post('/competitors/competitors/', newCompetitor),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    }
  });

  // Delete competitor mutation
  const deleteCompetitorMutation = useMutation({
    mutationFn: (id: number) =>
      api.delete(`/competitors/competitors/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    }
  });

  return <div>{/* Competitors list and management */}</div>;
}
```

---

### Competitor Detail (`/competitors/:id`)

```typescript
function CompetitorDetail() {
  const { id } = useParams();

  // Fetch competitor details
  const { data: competitor } = useQuery({
    queryKey: ['competitor', id],
    queryFn: () => api.get(`/competitors/competitors/${id}/`)
  });

  // Fetch competitor analytics
  const { data: analytics } = useQuery({
    queryKey: ['competitor-analytics', id],
    queryFn: () => api.get(
      `/competitors/competitor-analytics/?competitor=${id}`
    )
  });

  // Fetch competitor prompts
  const { data: prompts } = useQuery({
    queryKey: ['competitor-prompts', id],
    queryFn: () => api.get(
      `/competitors/competitor-prompts/?competitor=${id}`
    )
  });

  return <div>{/* Competitor detail page */}</div>;
}
```

---

### Content Gaps (`/content-gaps`)

```typescript
function ContentGaps() {
  // Fetch competitor prompts (where they appear but you don't)
  const { data: competitorPrompts } = useQuery({
    queryKey: ['competitor-prompts'],
    queryFn: () => api.get('/competitors/competitor-prompts/')
  });

  // Fetch your mentions
  const { data: yourMentions } = useQuery({
    queryKey: ['your-mentions'],
    queryFn: () => api.get('/prompts/mentions/')
  });

  // Calculate gaps
  const gaps = useMemo(() => {
    if (!competitorPrompts || !yourMentions) return [];
    
    return competitorPrompts.filter((cp: any) => 
      cp.your_mentions === 0 && cp.total_mentions > 10
    );
  }, [competitorPrompts, yourMentions]);

  return <div>{/* Content gaps analysis */}</div>;
}
```

---

### Organization Settings (`/organization-settings`)

```typescript
import { authService } from '@/services';

function OrganizationSettings() {
  // Fetch organization details
  const { data: org } = useQuery({
    queryKey: ['organization'],
    queryFn: () => api.get('/auth/organization/')
  });

  // Fetch team members
  const { data: teamMembers } = useQuery({
    queryKey: ['team-members'],
    queryFn: () => authService.getTeamMembers()
  });

  // Fetch domains
  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: () => api.get('/domains/')
  });

  // Send invitation mutation
  const inviteMutation = useMutation({
    mutationFn: (inviteData: any) =>
      authService.sendInvitation(inviteData),
    onSuccess: () => {
      toast.success('Invitation sent!');
    }
  });

  return <div>{/* Organization settings UI */}</div>;
}
```

---

### Team Member Permissions (`/organization-settings/members/:memberId`)

```typescript
import { authService } from '@/services';

function TeamMemberPermissions() {
  const { memberId } = useParams();

  // Fetch user details
  const { data: user } = useQuery({
    queryKey: ['user', memberId],
    queryFn: () => api.get(`/auth/team-members/${memberId}/`)
  });

  // Fetch user permissions
  const { data: permissions } = useQuery({
    queryKey: ['user-permissions', memberId],
    queryFn: () => authService.getUserPermissions(Number(memberId))
  });

  // Fetch available modules
  const { data: availableModules } = useQuery({
    queryKey: ['available-modules'],
    queryFn: () => authService.getAvailableModules()
  });

  // Assign permission mutation
  const assignMutation = useMutation({
    mutationFn: (module: string) =>
      authService.assignPermission(Number(memberId), module),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-permissions', memberId] });
    }
  });

  // Remove permission mutation
  const removeMutation = useMutation({
    mutationFn: (permissionId: number) =>
      authService.removePermission(permissionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-permissions', memberId] });
    }
  });

  return <div>{/* Permissions management UI */}</div>;
}
```

---

## 🔄 Complete API Reference

### Authentication
```typescript
// Login
POST /auth/login/
Body: { email, password }

// Logout
POST /auth/logout/

// Profile
GET /auth/profile/
PUT /auth/profile/update/
```

### Domains
```typescript
// List domains
GET /domains/

// Create domain
POST /domains/
Body: { name, url, organisation }

// Get domain
GET /domains/{id}/

// Update domain
PUT /domains/{id}/

// Delete domain
DELETE /domains/{id}/
```

### Mentions
```typescript
// List mentions
GET /prompts/mentions/
Params: ?platform=ChatGPT&sentiment=positive&page=1

// Get filters
GET /prompts/mentions/filters/

// Get mention detail
GET /prompts/mentions/{id}/

// Related mentions
GET /prompts/mentions/{id}/related/

// Trends
GET /prompts/mentions/trends/

// Export
POST /prompts/mentions/export/
```

### Prompts
```typescript
// Prompt groups
GET /prompts/groups/
POST /prompts/groups/
GET /prompts/groups/{id}/
PUT /prompts/groups/{id}/
DELETE /prompts/groups/{id}/

// Prompts
GET /prompts/prompts/
POST /prompts/prompts/
GET /prompts/prompts/{id}/
PUT /prompts/prompts/{id}/
DELETE /prompts/prompts/{id}/

// Analytics
GET /prompts/prompts/{id}/analytics/
```

### Alerts
```typescript
// Alerts
GET /alerts/alerts/
POST /alerts/alerts/
GET /alerts/alerts/{id}/
PUT /alerts/alerts/{id}/
DELETE /alerts/alerts/{id}/

// Rules
GET /alerts/alert-rules/
POST /alerts/alert-rules/
GET /alerts/alert-rules/{id}/
PUT /alerts/alert-rules/{id}/
DELETE /alerts/alert-rules/{id}/
```

### Analytics
```typescript
// Sentiment
GET /analytics/sentiment-analytics/
Params: ?timestamp__gte=2025-10-01&domain=1

// Share of Voice
GET /analytics/share-of-voice/
Params: ?timestamp__gte=2025-10-01&competitor=1
```

### Topics
```typescript
// Topics
GET /topics/topics/
POST /topics/topics/
GET /topics/topics/{id}/
PUT /topics/topics/{id}/
DELETE /topics/topics/{id}/

// Analytics
GET /topics/topic-analytics/

// Prompts
GET /topics/topic-prompts/
```

### Competitors
```typescript
// Competitors
GET /competitors/competitors/
POST /competitors/competitors/
GET /competitors/competitors/{id}/
PUT /competitors/competitors/{id}/
DELETE /competitors/competitors/{id}/

// Analytics
GET /competitors/competitor-analytics/

// Prompts
GET /competitors/competitor-prompts/
```

---

## 🎯 Next Steps

1. **Start Backend Server:**
   ```bash
   cd backend
   python manage.py runserver
   ```

2. **Start Frontend Dev Server:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test Login:**
   - Navigate to `/signin`
   - Use: `admin@llmmonitor.com` / `Admin@123`

4. **Integrate Pages One by One:**
   - Use the examples above for each page
   - Test API calls with React Query DevTools
   - Handle loading/error states

5. **Add Environment Variables:**
   ```env
   VITE_API_URL=http://localhost:8000
   ```

---

## ✅ Summary

**Database:** ✅ Loaded with 600+ seed records  
**APIs:** ✅ All endpoints functional  
**Auth Service:** ✅ Created  
**API Client:** ✅ Created  
**Integration Examples:** ✅ Provided for all pages  

**Your frontend is ready to connect to the backend!** 🚀

All you need to do is copy the integration examples into your page components and customize the UI rendering logic.

---

**Last Updated:** November 3, 2025  
**Status:** ✅ **READY FOR FRONTEND INTEGRATION**

