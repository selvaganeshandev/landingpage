from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Sum, Avg
from django.db import connection
from .models import Topic, TopicAnalytics, TopicPrompt
from .serializers import TopicSerializer, TopicAnalyticsSerializer, TopicPromptSerializer


class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Topic.objects.all()
        return Topic.objects.filter(domain__organisation=user.organisation)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get topics for a specific domain."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(domain_id=domain_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending topics based on growth."""
        domain_id = request.query_params.get('domain_id')
        queryset = self.get_queryset()
        
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        
        # Get topics with positive trend percentage
        trending = queryset.filter(trend_percentage__gt=0).order_by('-trend_percentage')[:10]
        serializer = self.get_serializer(trending, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def keyword_analytics(self, request, pk=None):
        """Get keyword analytics for a topic."""
        topic = self.get_object()
        
        # Query keyword_analytics table directly (from engine)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    k.keyword,
                    ka.platform,
                    ka.mentions,
                    ka.avg_position,
                    ka.visibility_score,
                    ka.sentiment_score,
                    ka.timestamp
                FROM keyword_analytics ka
                INNER JOIN topic_keywords tk ON ka.keyword_id = tk.keyword_id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE tk.topic_id = %s
                AND ka.track_status = 'COMP'
                ORDER BY ka.mentions DESC, ka.timestamp DESC
            """, [topic.id])
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Aggregate by keyword (sum across platforms)
        keyword_data = {}
        for row in results:
            keyword = row['keyword']
            if keyword not in keyword_data:
                keyword_data[keyword] = {
                    'keyword': keyword,
                    'mentions': 0,
                    'avg_position': 0.0,
                    'visibility_score': 0.0,
                    'sentiment_score': 0.0,
                    'platforms': []
                }
            keyword_data[keyword]['mentions'] += row['mentions'] or 0
            keyword_data[keyword]['platforms'].append(row['platform'])
        
        # Calculate averages
        for keyword in keyword_data.values():
            keyword['platforms'] = list(set(keyword['platforms']))
        
        return Response(list(keyword_data.values()))
    
    @action(detail=True, methods=['get'])
    def related_prompts(self, request, pk=None):
        """Get prompts related to a topic via keywords."""
        topic = self.get_object()
        
        # Query prompts linked to topic keywords
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT
                    p.id,
                    p.prompt as prompt_text,
                    pg.theme as group_theme,
                    COUNT(DISTINCT pa.id) as analytics_count,
                    AVG(pa.position) as avg_position,
                    AVG(pa.sentiment_score) as avg_sentiment,
                    SUM(pa.total_mentions) as mentions,
                    CASE 
                        WHEN AVG(pa.position) IS NOT NULL THEN 
                            CAST((100.0 - LEAST(AVG(pa.position) * 10, 100.0)) AS INTEGER)
                        ELSE 0
                    END as relevance_score
                FROM prompts p
                INNER JOIN prompt_keywords pk ON p.id = pk.prompt_id
                INNER JOIN topic_keywords tk ON pk.keyword_id = tk.keyword_id
                INNER JOIN prompt_groups pg ON p.group_id = pg.id
                LEFT JOIN prompt_analytics pa ON p.id = pa.prompt_id AND pa.track_status = 'COMP'
                WHERE tk.topic_id = %s
                GROUP BY p.id, p.prompt, pg.theme
                ORDER BY mentions DESC NULLS LAST
                LIMIT 50
            """, [topic.id])
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Transform decimal values to float for JSON serialization
        for result in results:
            if result['avg_position'] is not None:
                result['avg_position'] = float(result['avg_position'])
            if result['avg_sentiment'] is not None:
                result['avg_sentiment'] = float(result['avg_sentiment'])
            if result['mentions'] is None:
                result['mentions'] = 0
        
        return Response(results)


class TopicAnalyticsViewSet(viewsets.ModelViewSet):
    serializer_class = TopicAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = TopicAnalytics.objects.all() if user.role == 'super_admin' else TopicAnalytics.objects.filter(
            topic__domain__organisation=user.organisation
        )
        
        # Support filtering by topic_id in query params
        topic_id = self.request.query_params.get('topic_id')
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get time-series trends for topics."""
        topic_id = request.query_params.get('topic_id')
        days = int(request.query_params.get('days', 30))
        
        queryset = self.get_queryset()
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        # Get data for the last N days
        start_date = timezone.now().date() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=start_date)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TopicPromptViewSet(viewsets.ModelViewSet):
    serializer_class = TopicPromptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = TopicPrompt.objects.all() if user.role == 'super_admin' else TopicPrompt.objects.filter(
            topic__domain__organisation=user.organisation
        )
        
        # Support filtering by topic_id in query params
        topic_id = self.request.query_params.get('topic_id')
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def high_relevance(self, request):
        """Get prompts with high relevance scores."""
        topic_id = request.query_params.get('topic_id')
        min_score = int(request.query_params.get('min_score', 80))
        
        queryset = self.get_queryset().filter(relevance_score__gte=min_score)
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

