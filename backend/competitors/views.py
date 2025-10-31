from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg
from datetime import timedelta
from django.utils import timezone
from .models import Competitor, CompetitorAnalytics, CompetitorPrompt
from .serializers import (
    CompetitorSerializer, CompetitorAnalyticsSerializer, CompetitorPromptSerializer
)


class CompetitorViewSet(viewsets.ModelViewSet):
    serializer_class = CompetitorSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Competitor.objects.all()
        return Competitor.objects.filter(domain__organisation=user.organisation)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get competitors for a specific domain."""
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
    def comparison(self, request):
        """Get competitive comparison data."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        competitors = self.get_queryset().filter(domain_id=domain_id)
        
        data = {
            'competitors': CompetitorSerializer(competitors, many=True).data,
            'summary': {
                'total_competitors': competitors.count(),
                'avg_mentions': competitors.aggregate(Avg('mentions'))['mentions__avg'] or 0,
                'total_market_mentions': competitors.aggregate(Sum('mentions'))['mentions__sum'] or 0,
            }
        }
        return Response(data)


class CompetitorAnalyticsViewSet(viewsets.ModelViewSet):
    serializer_class = CompetitorAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return CompetitorAnalytics.objects.all()
        return CompetitorAnalytics.objects.filter(
            competitor__domain__organisation=user.organisation
        )
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get time-series trends for competitors."""
        competitor_id = request.query_params.get('competitor_id')
        days = int(request.query_params.get('days', 30))
        
        queryset = self.get_queryset()
        if competitor_id:
            queryset = queryset.filter(competitor_id=competitor_id)
        
        # Get data for the last N days
        start_date = timezone.now().date() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=start_date)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CompetitorPromptViewSet(viewsets.ModelViewSet):
    serializer_class = CompetitorPromptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return CompetitorPrompt.objects.all()
        return CompetitorPrompt.objects.filter(
            competitor__domain__organisation=user.organisation
        )
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def answer_gaps(self, request):
        """Get prompts where competitors dominate (answer gap analysis)."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get prompts where competitor mentions are high and your mentions are low
        queryset = self.get_queryset().filter(
            competitor__domain_id=domain_id,
            mentions__gte=10,  # At least 10 competitor mentions
            your_mentions__lt=5  # Less than 5 of your mentions
        ).order_by('-mentions')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

