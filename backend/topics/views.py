from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from django.utils import timezone
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


class TopicAnalyticsViewSet(viewsets.ModelViewSet):
    serializer_class = TopicAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return TopicAnalytics.objects.all()
        return TopicAnalytics.objects.filter(
            topic__domain__organisation=user.organisation
        )
    
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
        if user.role == 'super_admin':
            return TopicPrompt.objects.all()
        return TopicPrompt.objects.filter(
            topic__domain__organisation=user.organisation
        )
    
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

