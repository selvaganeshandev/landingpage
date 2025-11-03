# Frontend Data Access with Partitioned Tables

## The Simple Truth: No Changes Required! 🎉

**Table partitioning is completely transparent to your application.** Your Django views, serializers, and frontend API calls work exactly the same whether tables are partitioned or not.

---

## How PostgreSQL Handles Partitions

### Behind the Scenes

```python
# Your Django view code:
PromptAnalytics.objects.filter(
    prompt_id=123,
    created_at__gte='2025-10-01'
)

# PostgreSQL automatically:
# 1. Analyzes the WHERE clause
# 2. Determines which partition(s) contain the data
# 3. Only scans those partitions
# 4. Returns results as if it's a single table
```

**You write:** Query the parent table
**PostgreSQL does:** Smart partition routing
**You get:** Fast results from relevant partitions

---

## Real-World Examples

### Example 1: Dashboard Analytics (Last 30 Days)

**Backend View:**
```python
# backend/prompts/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import PromptAnalytics
from .serializers import PromptAnalyticsSerializer

@api_view(['GET'])
def get_prompt_analytics(request, prompt_id):
    """Get analytics for a specific prompt (last 30 days)"""
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # 🎯 Same query works with partitioned tables!
    analytics = PromptAnalytics.objects.filter(
        prompt_id=prompt_id,
        created_at__gte=thirty_days_ago
    ).order_by('-created_at')
    
    # PostgreSQL automatically:
    # - Scans only prompt_analytics_2025_10 and prompt_analytics_2025_11
    # - Skips all other partitions
    # - Returns results 10-50x faster!
    
    serializer = PromptAnalyticsSerializer(analytics, many=True)
    return Response(serializer.data)
```

**Frontend Call:**
```typescript
// frontend/src/api/prompts.ts

export async function getPromptAnalytics(promptId: number) {
  const response = await fetch(
    `/api/prompts/${promptId}/analytics/`
  );
  return response.json();
}

// Usage in React component:
const { data } = useQuery(['prompt-analytics', promptId], 
  () => getPromptAnalytics(promptId)
);

// ✅ Works exactly the same with partitioned tables!
// ✅ Just faster! ⚡
```

---

### Example 2: Competitor Analytics Chart (Date Range)

**Backend View:**
```python
# backend/competitors/views.py

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from .models import Competitor, CompetitorAnalytics

class CompetitorViewSet(ModelViewSet):
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get competitor analytics for date range"""
        
        competitor = self.get_object()
        
        # Get date range from query params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # 🎯 Query works with partitioned tables!
        analytics = CompetitorAnalytics.objects.filter(
            competitor=competitor,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
        
        # PostgreSQL partition pruning happens automatically:
        # If date range is Oct 1-31, only scans competitor_analytics_2025_10
        
        serializer = CompetitorAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)
```

**Frontend Call:**
```typescript
// frontend/src/api/competitors.ts

interface AnalyticsParams {
  competitorId: number;
  startDate: string;
  endDate: string;
}

export async function getCompetitorAnalytics({ 
  competitorId, 
  startDate, 
  endDate 
}: AnalyticsParams) {
  const response = await fetch(
    `/api/competitors/${competitorId}/analytics/?` +
    `start_date=${startDate}&end_date=${endDate}`
  );
  return response.json();
}

// Usage in chart component:
function CompetitorChart({ competitorId }) {
  const { data } = useQuery(
    ['competitor-analytics', competitorId, dateRange],
    () => getCompetitorAnalytics({
      competitorId,
      startDate: '2025-10-01',
      endDate: '2025-10-31'
    })
  );
  
  // ✅ Same API, same response format
  // ✅ Just faster with partitioned tables!
  
  return <LineChart data={data} />;
}
```

---

### Example 3: Monthly Report (Specific Month)

**Backend View:**
```python
# backend/analytics/views.py

@api_view(['GET'])
def monthly_sentiment_report(request):
    """Get sentiment analytics for a specific month"""
    
    year = request.query_params.get('year', 2025)
    month = request.query_params.get('month', 10)
    
    # Create date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # 🎯 Query the partitioned table
    sentiment_data = SentimentAnalytics.objects.filter(
        timestamp__gte=start_date,
        timestamp__lt=end_date
    ).values('theme').annotate(
        avg_positive=Avg('positive_percentage'),
        avg_negative=Avg('negative_percentage'),
        total_mentions=Sum('mention_count')
    )
    
    # PostgreSQL only scans sentiment_analytics_2025_10 partition
    # Blazing fast! ⚡
    
    return Response(sentiment_data)
```

**Frontend Call:**
```typescript
// frontend/src/api/analytics.ts

export async function getMonthlyReport(year: number, month: number) {
  const response = await fetch(
    `/api/analytics/monthly-report/?year=${year}&month=${month}`
  );
  return response.json();
}

// Usage in dashboard:
function MonthlyDashboard() {
  const { data } = useQuery(
    ['monthly-report', 2025, 10],
    () => getMonthlyReport(2025, 10)
  );
  
  // ✅ Zero changes to frontend code!
  
  return <SentimentReport data={data} />;
}
```

---

## Pagination with Partitioned Tables

Pagination works exactly the same:

**Backend:**
```python
# backend/prompts/views.py

from rest_framework.pagination import PageNumberPagination

class PromptAnalyticsViewSet(ModelViewSet):
    queryset = PromptAnalytics.objects.all()
    serializer_class = PromptAnalyticsSerializer
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range (enables partition pruning)
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        return queryset.order_by('-created_at')
```

**Frontend:**
```typescript
// frontend/src/hooks/usePromptAnalytics.ts

export function usePromptAnalytics(page: number, startDate?: string) {
  return useQuery(
    ['prompt-analytics', page, startDate],
    () => fetch(
      `/api/prompt-analytics/?page=${page}` + 
      (startDate ? `&start_date=${startDate}` : '')
    ).then(res => res.json())
  );
}

// Usage:
function AnalyticsList() {
  const [page, setPage] = useState(1);
  const { data } = usePromptAnalytics(page, '2025-10-01');
  
  // ✅ Pagination works perfectly with partitioned tables!
  
  return (
    <>
      <Table data={data.results} />
      <Pagination 
        page={page} 
        count={data.count}
        onChange={setPage}
      />
    </>
  );
}
```

---

## Aggregations with Partitioned Tables

Aggregations (COUNT, AVG, SUM) work seamlessly:

**Backend:**
```python
# backend/analytics/views.py

from django.db.models import Count, Avg, Sum

@api_view(['GET'])
def platform_summary(request):
    """Get summary stats by platform (last 90 days)"""
    
    ninety_days_ago = timezone.now() - timedelta(days=90)
    
    # 🎯 Aggregation across multiple partitions
    summary = PromptAnalytics.objects.filter(
        created_at__gte=ninety_days_ago
    ).values('platform').annotate(
        total_mentions=Sum('total_mentions'),
        total_citations=Sum('total_citations'),
        avg_visibility=Avg('visibility_score'),
        record_count=Count('id')
    ).order_by('-total_mentions')
    
    # PostgreSQL automatically:
    # - Scans 3 partitions (Oct, Nov, Dec)
    # - Aggregates results from each partition
    # - Returns combined results
    
    return Response(summary)
```

**Frontend:**
```typescript
// frontend/src/api/analytics.ts

export async function getPlatformSummary() {
  const response = await fetch('/api/analytics/platform-summary/');
  return response.json();
}

// Usage in dashboard:
function PlatformStats() {
  const { data } = useQuery('platform-summary', getPlatformSummary);
  
  // ✅ Gets aggregated data from multiple partitions
  // ✅ Frontend code unchanged!
  
  return (
    <div>
      {data.map(platform => (
        <StatCard key={platform.platform} {...platform} />
      ))}
    </div>
  );
}
```

---

## Joins with Partitioned Tables

Joins work normally, even between partitioned and non-partitioned tables:

**Backend:**
```python
# backend/prompts/views.py

@api_view(['GET'])
def prompt_with_analytics(request, prompt_id):
    """Get prompt with its recent analytics"""
    
    prompt = Prompt.objects.get(id=prompt_id)
    
    # 🎯 Join partitioned table with regular table
    recent_analytics = PromptAnalytics.objects.filter(
        prompt=prompt,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('prompt').order_by('-created_at')[:10]
    
    # PostgreSQL handles the join efficiently
    
    return Response({
        'prompt': PromptSerializer(prompt).data,
        'recent_analytics': PromptAnalyticsSerializer(
            recent_analytics, many=True
        ).data
    })
```

**Frontend:**
```typescript
// frontend/src/components/PromptDetail.tsx

function PromptDetail({ promptId }) {
  const { data } = useQuery(
    ['prompt-detail', promptId],
    () => fetch(`/api/prompts/${promptId}/with-analytics/`)
      .then(res => res.json())
  );
  
  // ✅ Gets data from both regular and partitioned tables
  // ✅ No frontend changes!
  
  return (
    <div>
      <h1>{data.prompt.text}</h1>
      <AnalyticsTable data={data.recent_analytics} />
    </div>
  );
}
```

---

## Query Optimization Tips

To get the BEST performance from partitioned tables:

### ✅ DO: Always Include Date Filter

```python
# ✅ GOOD: Enables partition pruning
PromptAnalytics.objects.filter(
    prompt_id=123,
    created_at__gte='2025-10-01',  # ← Partition key in WHERE clause
    created_at__lt='2025-11-01'
)
# → Scans only prompt_analytics_2025_10

# ❌ BAD: Scans ALL partitions (slow!)
PromptAnalytics.objects.filter(
    prompt_id=123
    # No date filter = scans all partitions
)
```

### ✅ DO: Use Date Ranges in API

```python
# backend/prompts/views.py

class PromptAnalyticsViewSet(ModelViewSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Encourage clients to provide date ranges
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if not start_date:
            # Default to last 30 days if not specified
            start_date = timezone.now() - timedelta(days=30)
        
        queryset = queryset.filter(created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
```

**Frontend:**
```typescript
// Always include date range in API calls
export function usePromptAnalytics(promptId: number, dateRange: DateRange) {
  return useQuery(
    ['prompt-analytics', promptId, dateRange],
    () => fetch(
      `/api/prompt-analytics/?` +
      `prompt_id=${promptId}&` +
      `start_date=${dateRange.start}&` +
      `end_date=${dateRange.end}`
    ).then(res => res.json())
  );
}
```

### ✅ DO: Use Indexes on Partitions

Indexes are automatically created on each partition:

```python
class PromptAnalytics(models.Model):
    class Meta:
        indexes = [
            # These indexes exist on EACH partition
            models.Index(fields=['prompt', 'platform', 'created_at']),
            models.Index(fields=['platform', 'created_at']),
            models.Index(fields=['is_mention', 'created_at']),
        ]
```

---

## Monitoring Partition Usage

Verify that partition pruning is working:

```python
# backend/management/commands/check_partition_usage.py

from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Explain a typical query
            cursor.execute("""
                EXPLAIN (ANALYZE, BUFFERS)
                SELECT * FROM prompt_analytics
                WHERE created_at >= NOW() - INTERVAL '30 days'
                  AND prompt_id = 123;
            """)
            
            for row in cursor.fetchall():
                self.stdout.write(str(row))
```

**Expected output:**
```
Seq Scan on prompt_analytics_2025_10
Seq Scan on prompt_analytics_2025_11
↑ Only scans 2 partitions, not all!
```

---

## Common Frontend Patterns

### Pattern 1: Date Range Picker

```typescript
// frontend/src/components/AnalyticsDashboard.tsx

function AnalyticsDashboard() {
  const [dateRange, setDateRange] = useState({
    start: subDays(new Date(), 30),
    end: new Date()
  });
  
  const { data } = useQuery(
    ['analytics', dateRange],
    () => fetch(
      `/api/analytics/?` +
      `start_date=${format(dateRange.start, 'yyyy-MM-dd')}&` +
      `end_date=${format(dateRange.end, 'yyyy-MM-dd')}`
    ).then(res => res.json())
  );
  
  return (
    <div>
      <DateRangePicker value={dateRange} onChange={setDateRange} />
      <AnalyticsChart data={data} />
    </div>
  );
}
```

### Pattern 2: Time Period Selector

```typescript
// frontend/src/components/TimePeriodSelector.tsx

function CompetitorAnalytics({ competitorId }) {
  const [period, setPeriod] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  
  const { data } = useQuery(
    ['competitor-analytics', competitorId, period],
    () => fetch(
      `/api/competitors/${competitorId}/analytics/?period=${period}`
    ).then(res => res.json())
  );
  
  return (
    <div>
      <ButtonGroup>
        <Button onClick={() => setPeriod('7d')}>7 Days</Button>
        <Button onClick={() => setPeriod('30d')}>30 Days</Button>
        <Button onClick={() => setPeriod('90d')}>90 Days</Button>
        <Button onClick={() => setPeriod('1y')}>1 Year</Button>
      </ButtonGroup>
      <Chart data={data} />
    </div>
  );
}
```

### Pattern 3: Infinite Scroll

```typescript
// frontend/src/hooks/useInfiniteAnalytics.ts

export function useInfiniteAnalytics(promptId: number) {
  return useInfiniteQuery(
    ['prompt-analytics', promptId],
    async ({ pageParam = 1 }) => {
      const response = await fetch(
        `/api/prompt-analytics/?` +
        `prompt_id=${promptId}&` +
        `page=${pageParam}&` +
        `start_date=${format(subDays(new Date(), 90), 'yyyy-MM-dd')}`
      );
      return response.json();
    },
    {
      getNextPageParam: (lastPage) => lastPage.next,
    }
  );
}

// Usage:
function AnalyticsList({ promptId }) {
  const { data, fetchNextPage, hasNextPage } = useInfiniteAnalytics(promptId);
  
  // ✅ Infinite scroll works perfectly with partitioned tables
  
  return (
    <InfiniteScroll onLoadMore={fetchNextPage} hasMore={hasNextPage}>
      {data.pages.map(page => 
        page.results.map(item => <AnalyticsRow key={item.id} {...item} />)
      )}
    </InfiniteScroll>
  );
}
```

---

## Real-Time Updates

Even real-time subscriptions work the same:

```python
# backend/prompts/consumers.py (WebSocket)

class AnalyticsConsumer(WebsocketConsumer):
    def receive(self, text_data):
        data = json.loads(text_data)
        prompt_id = data['prompt_id']
        
        # Query partitioned table
        latest_analytics = PromptAnalytics.objects.filter(
            prompt_id=prompt_id,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).order_by('-created_at').first()
        
        # Send to frontend
        self.send(text_data=json.dumps({
            'analytics': PromptAnalyticsSerializer(latest_analytics).data
        }))
```

```typescript
// frontend/src/hooks/useRealtimeAnalytics.ts

export function useRealtimeAnalytics(promptId: number) {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/analytics/');
    
    ws.onmessage = (event) => {
      const analytics = JSON.parse(event.data);
      setData(analytics);
    };
    
    ws.send(JSON.stringify({ prompt_id: promptId }));
    
    return () => ws.close();
  }, [promptId]);
  
  return data;
}

// ✅ Real-time updates work with partitioned tables!
```

---

## Summary: Zero Frontend Changes! 🎉

### What Stays the Same

✅ **API endpoints** - Same URLs, same parameters
✅ **Response format** - Same JSON structure
✅ **Serializers** - No changes needed
✅ **Query patterns** - Same Django ORM queries
✅ **Frontend code** - Zero changes to React/TypeScript
✅ **API client** - Same fetch/axios calls
✅ **State management** - Same React Query/Redux logic

### What Gets Better

🚀 **Performance** - 10-50x faster queries
🚀 **Scalability** - Handle millions of rows easily
🚀 **Maintenance** - Easy data archival/deletion
🚀 **User experience** - Faster page loads

### The Magic

PostgreSQL does ALL the work behind the scenes:
1. Analyzes your WHERE clause
2. Determines relevant partitions
3. Only scans those partitions
4. Returns results as if it's one table
5. Your app never knows the difference!

---

## Quick Checklist

When implementing partitioned tables:

- ✅ **Backend:** No Django view changes needed
- ✅ **Backend:** Keep using same ORM queries
- ✅ **Backend:** Add date filters for best performance
- ✅ **Frontend:** No API changes needed
- ✅ **Frontend:** No component changes needed
- ✅ **Frontend:** Same data fetching logic
- ✅ **Testing:** Test with date range queries
- ✅ **Monitoring:** Verify partition pruning works

---

**Bottom Line:** Implement partitioning for performance gains without touching a single line of frontend code! 🎉

---

**Last Updated:** November 3, 2025

