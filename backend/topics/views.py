from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Sum, Avg
from django.db import connection
from .models import Topic, TopicAnalytics
from .serializers import TopicSerializer, TopicAnalyticsSerializer


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
    
    @action(detail=True, methods=['get'])
    def optimize(self, request, pk=None):
        """Get AI-powered optimization recommendations for a topic."""
        topic = self.get_object()
        
        try:
            # Get topic analytics data (TopicAnalytics doesn't have track_status field)
            latest_analytics = TopicAnalytics.objects.filter(
                topic=topic
            ).order_by('-timestamp').first()
            
            # Get topic keywords
            from topics.models import TopicKeyword
            topic_keywords = TopicKeyword.objects.filter(topic=topic).select_related('keyword')
            keyword_list = [tk.keyword.keyword for tk in topic_keywords]
            
            # Get keyword analytics for performance insights
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        k.keyword,
                        SUM(ka.mentions) as total_mentions,
                        AVG(ka.avg_position) as avg_position,
                        AVG(ka.visibility_score) as avg_visibility,
                        AVG(ka.sentiment_score) as avg_sentiment
                    FROM keyword_analytics ka
                    INNER JOIN topic_keywords tk ON ka.keyword_id = tk.keyword_id
                    INNER JOIN keywords k ON ka.keyword_id = k.id
                    WHERE tk.topic_id = %s
                    AND ka.track_status = 'COMP'
                    GROUP BY k.keyword
                    ORDER BY total_mentions DESC
                """, [topic.id])
                
                columns = [col[0] for col in cursor.description]
                keyword_performance = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Convert Decimal values to proper types for JSON serialization
            for kw_perf in keyword_performance:
                if kw_perf.get('total_mentions') is not None:
                    kw_perf['total_mentions'] = int(kw_perf['total_mentions'])
                if kw_perf.get('avg_position') is not None:
                    kw_perf['avg_position'] = float(kw_perf['avg_position'])
                if kw_perf.get('avg_visibility') is not None:
                    kw_perf['avg_visibility'] = float(kw_perf['avg_visibility'])
                if kw_perf.get('avg_sentiment') is not None:
                    kw_perf['avg_sentiment'] = float(kw_perf['avg_sentiment'])
            
            # Get related prompts for content analysis
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT p.prompt as prompt_text
                    FROM prompts p
                    INNER JOIN prompt_keywords pk ON p.id = pk.prompt_id
                    INNER JOIN topic_keywords tk ON pk.keyword_id = tk.keyword_id
                    WHERE tk.topic_id = %s
                    LIMIT 20
                """, [topic.id])
                
                existing_prompts = [row[0] for row in cursor.fetchall()]
            
            # Calculate current metrics (convert Decimal to float for JSON serialization)
            current_visibility = float(latest_analytics.visibility_score) if latest_analytics else 0.0
            current_sentiment = float(latest_analytics.sentiment_score) if latest_analytics else 0.0
            current_mentions = int(latest_analytics.total_mentions) if latest_analytics else 0
            
            # Generate recommendations based on data analysis
            recommendations = {
                'keywords': [],
                'contentGaps': [],
                'prompts': [],
                'competitive': [],
                'actions': []
            }
            
            # Keyword recommendations - suggest related keywords with high potential
            if keyword_performance:
                top_keyword = keyword_performance[0]
                # Suggest variations and related terms
                base_keyword = top_keyword['keyword']
                recommendations['keywords'] = [
                    {
                        'keyword': f"{base_keyword} guide",
                        'impact': 'high' if top_keyword['total_mentions'] > 100 else 'medium',
                        'difficulty': 'low'
                    },
                    {
                        'keyword': f"best {base_keyword}",
                        'impact': 'high',
                        'difficulty': 'medium'
                    },
                    {
                        'keyword': f"{base_keyword} tips",
                        'impact': 'medium',
                        'difficulty': 'low'
                    },
                    {
                        'keyword': f"{base_keyword} review",
                        'impact': 'medium',
                        'difficulty': 'medium'
                    }
                ]
            
            # Content gaps based on visibility and sentiment
            if current_visibility < 50:
                recommendations['contentGaps'].append({
                    'gap': 'Improve search visibility with comprehensive guides',
                    'priority': 'high',
                    'potential': f'+{int((50 - current_visibility) * 0.3)}% visibility'
                })
            
            if current_sentiment < 60:
                recommendations['contentGaps'].append({
                    'gap': 'Enhance positive sentiment with success stories',
                    'priority': 'high',
                    'potential': f'+{int((60 - current_sentiment) * 0.2)}% sentiment'
                })
            
            if not existing_prompts or len(existing_prompts) < 5:
                recommendations['contentGaps'].append({
                    'gap': 'Expand content coverage with more prompt variations',
                    'priority': 'medium',
                    'potential': '+15% engagement'
                })
            
            # Prompt suggestions based on existing keywords
            if keyword_list:
                base_keyword = keyword_list[0]
                recommendations['prompts'] = [
                    f"best {base_keyword} for beginners",
                    f"complete guide to {base_keyword}",
                    f"{base_keyword} vs alternatives",
                    f"how to optimize {base_keyword}",
                    f"expert tips for {base_keyword}"
                ]
            
            # Competitive positioning advice
            if current_visibility < 70:
                recommendations['competitive'].append({
                    'insight': 'Focus on long-tail keyword variations to capture niche searches',
                    'impact': 'high'
                })
            
            if current_sentiment < 70:
                recommendations['competitive'].append({
                    'insight': 'Emphasize unique value propositions and benefits',
                    'impact': 'high'
                })
            
            recommendations['competitive'].append({
                'insight': 'Create comparison content to differentiate from competitors',
                'impact': 'medium'
            })
            
            # Action plan based on current performance
            priority = 1
            if current_visibility < 50:
                recommendations['actions'].append({
                    'action': f'Improve visibility by targeting high-volume keywords related to "{topic.name}"',
                    'priority': priority
                })
                priority += 1
            
            if current_sentiment < 60:
                recommendations['actions'].append({
                    'action': 'Create positive content showcasing benefits and success stories',
                    'priority': priority
                })
                priority += 1
            
            if len(keyword_list) < 5:
                recommendations['actions'].append({
                    'action': 'Expand keyword coverage to capture more search variations',
                    'priority': priority
                })
                priority += 1
            
            recommendations['actions'].append({
                'action': 'Monitor competitor content and identify differentiation opportunities',
                'priority': priority
            })
            
            return Response({
                'topic_id': topic.id,
                'topic_name': topic.name,
                'current_metrics': {
                    'visibility': current_visibility,
                    'sentiment': current_sentiment,
                    'mentions': current_mentions,
                    'keyword_count': len(keyword_list)
                },
                'recommendations': recommendations
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate recommendations: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))

        queryset = self.get_queryset()

        # Filter by domain_id if provided
        if domain_id:
            queryset = queryset.filter(topic__domain_id=domain_id)

        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)

        # Get data for the last N days
        start_date = timezone.now().date() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=start_date)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='distribution')
    def topic_distribution(self, request):
        """Get topic distribution data for pie chart (domain-based)."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get topics for the domain with their mentions
        topics = Topic.objects.filter(domain_id=domain_id).values(
            'id', 'name', 'total_mentions'
        ).order_by('-total_mentions')
        
        # Format for frontend pie chart
        distribution_data = [
            {
                'name': topic['name'],
                'value': topic['total_mentions'],
                'topic_id': topic['id']
            }
            for topic in topics
        ]
        
        return Response(distribution_data)
    
    @action(detail=False, methods=['get'], url_path='keyword-performance')
    def keyword_performance(self, request):
        """Get aggregated keyword performance across all topics in a domain."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        limit = int(request.query_params.get('limit', 10))
        
        # Query keyword analytics aggregated by keyword across all topics in domain
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    k.keyword,
                    SUM(ka.mentions) as total_mentions,
                    AVG(ka.avg_position) as avg_position,
                    AVG(ka.visibility_score) as visibility_score,
                    AVG(ka.sentiment_score) as sentiment_score,
                    COUNT(DISTINCT ka.platform) as platform_count,
                    ARRAY_AGG(DISTINCT ka.platform) as platforms
                FROM keyword_analytics ka
                INNER JOIN topic_keywords tk ON ka.keyword_id = tk.keyword_id
                INNER JOIN topics t ON tk.topic_id = t.id
                INNER JOIN keywords k ON ka.keyword_id = k.id
                WHERE t.domain_id = %s
                AND ka.track_status = 'COMP'
                GROUP BY k.keyword
                ORDER BY total_mentions DESC
                LIMIT %s
            """, [domain_id, limit])
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Convert decimal values to float for JSON serialization
        for result in results:
            result['avg_position'] = float(result['avg_position']) if result['avg_position'] else 0.0
            result['visibility_score'] = float(result['visibility_score']) if result['visibility_score'] else 0.0
            result['sentiment_score'] = float(result['sentiment_score']) if result['sentiment_score'] else 0.0
            result['total_mentions'] = int(result['total_mentions']) if result['total_mentions'] else 0
        
        return Response(results)
    
    @action(detail=False, methods=['get'], url_path='prompt-suggestions')
    def prompt_suggestions(self, request):
        """Get prompt suggestions - existing prompts on load, or generate new ones with ChatGPT."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        limit = int(request.query_params.get('limit', 6))
        generate_new = request.query_params.get('generate_new', 'false').lower() == 'true'
        
        # If not generating new, return existing prompts from database
        if not generate_new:
            try:
                # Query existing prompts linked to topics in the domain
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            sub.id,
                            sub.prompt_text,
                            sub.topic_name,
                            sub.keyword
                        FROM (
                            SELECT DISTINCT ON (p.id)
                                p.id,
                                p.prompt as prompt_text,
                                t.name as topic_name,
                                k.keyword,
                                p.created_at
                            FROM prompts p
                            INNER JOIN prompt_keywords pk ON p.id = pk.prompt_id
                            INNER JOIN keywords k ON pk.keyword_id = k.id
                            INNER JOIN topic_keywords tk ON k.id = tk.keyword_id
                            INNER JOIN topics t ON tk.topic_id = t.id
                            WHERE t.domain_id = %s
                            ORDER BY p.id, p.created_at DESC
                        ) sub
                        ORDER BY sub.created_at DESC
                        LIMIT %s
                    """, [domain_id, limit])
                    
                    columns = [col[0] for col in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Format response
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        'prompt_text': result.get('prompt_text', ''),
                        'topic_name': result.get('topic_name', 'General'),
                        'keyword': result.get('keyword', '')
                    })
                
                return Response(formatted_results)
                
            except Exception as e:
                return Response(
                    {'error': f'Failed to fetch existing prompts: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Generate new prompts using ChatGPT
        try:
            # Import ChatGPTClient from engine
            import sys
            import os
            from pathlib import Path
            
            # Get the project root (assuming backend is in backend/ and engine is in engine/)
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            engine_path = project_root / 'engine'
            
            if str(engine_path) not in sys.path:
                sys.path.insert(0, str(engine_path))
            
            from core.chatgpt_client import ChatGPTClient
            
            # Get topics for the domain with their keywords
            topics = Topic.objects.filter(domain_id=domain_id).prefetch_related('topic_keywords__keyword')
            
            if not topics.exists():
                return Response(
                    {'error': 'No topics found for this domain'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Collect all keywords from all topics
            all_keywords = []
            topic_keyword_map = {}  # Map to track which topic each keyword belongs to
            
            for topic in topics:
                topic_keywords = topic.topic_keywords.all()
                for tk in topic_keywords:
                    keyword_text = tk.keyword.keyword
                    all_keywords.append(keyword_text)
                    if keyword_text not in topic_keyword_map:
                        topic_keyword_map[keyword_text] = []
                    topic_keyword_map[keyword_text].append(topic.name)
            
            if not all_keywords:
                return Response(
                    {'error': 'No keywords found for topics in this domain'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Use ChatGPT to generate prompts based on topics and keywords
            chatgpt_client = ChatGPTClient()
            
            # Get domain name for context
            from domains.models import Domain
            domain = None
            try:
                domain = Domain.objects.get(id=domain_id)
                domain_name = domain.name
                country = getattr(domain, 'country', 'United States') or 'United States'
            except Domain.DoesNotExist:
                domain_name = "the domain"
                country = 'United States'
            
            # Generate prompts using ChatGPT
            # Use a subset of keywords if there are too many (ChatGPT has token limits)
            keywords_to_use = all_keywords[:20] if len(all_keywords) > 20 else all_keywords
            
            # Generate prompts
            generated_prompts = chatgpt_client.generate_prompts_from_keywords(
                keywords_to_use,
                domain_name,
                country=country
            )
            
            # Limit to requested number
            generated_prompts = generated_prompts[:limit]
            
            # Format response
            results = []
            for prompt_data in generated_prompts:
                prompt_text = prompt_data.get('prompt_text') or prompt_data.get('prompt', '').strip()
                keyword = prompt_data.get('keyword', '').strip()
                
                if prompt_text:
                    # Find which topic(s) this keyword belongs to
                    topic_names = topic_keyword_map.get(keyword, [])
                    topic_name = topic_names[0] if topic_names else "General"
                    
                    results.append({
                        'prompt_text': prompt_text,
                        'topic_name': topic_name,
                        'keyword': keyword
                    })
            
            # If we don't have enough prompts, generate more variations
            if len(results) < limit:
                # Generate additional prompts with different variations
                additional_keywords = all_keywords[20:40] if len(all_keywords) > 20 else all_keywords
                if additional_keywords:
                    additional_prompts = chatgpt_client.generate_prompts_from_keywords(
                        additional_keywords[:10],
                        domain_name,
                        country=country
                    )
                    
                    for prompt_data in additional_prompts:
                        if len(results) >= limit:
                            break
                        prompt_text = prompt_data.get('prompt_text') or prompt_data.get('prompt', '').strip()
                        keyword = prompt_data.get('keyword', '').strip()
                        
                        if prompt_text:
                            topic_names = topic_keyword_map.get(keyword, [])
                            topic_name = topic_names[0] if topic_names else "General"
                            
                            results.append({
                                'prompt_text': prompt_text,
                                'topic_name': topic_name,
                                'keyword': keyword
                            })
            
            return Response(results[:limit])
            
        except ImportError as e:
            return Response(
                {'error': f'Failed to import ChatGPTClient: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate prompts: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

