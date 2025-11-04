from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg
from .models import SentimentAnalytics, ShareOfVoiceAnalytics
from .serializers import SentimentAnalyticsSerializer, ShareOfVoiceAnalyticsSerializer


class SentimentAnalyticsViewSet(viewsets.ModelViewSet):
    serializer_class = SentimentAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return SentimentAnalytics.objects.all()
        return SentimentAnalytics.objects.filter(domain__organisation=user.organisation)
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get sentiment analytics for a specific domain."""
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))
        
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_date = timezone.now().date() - timedelta(days=days)
        queryset = self.get_queryset().filter(
            domain_id=domain_id,
            timestamp__gte=start_date
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get sentiment summary for a domain."""
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 7))
        
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_date = timezone.now().date() - timedelta(days=days)
        queryset = self.get_queryset().filter(
            domain_id=domain_id,
            timestamp__gte=start_date
        )
        
        # Calculate weighted averages
        total_mentions = queryset.aggregate(Sum('mention_count'))['mention_count__sum'] or 0
        
        if total_mentions == 0:
            return Response({
                'positive_percentage': 0,
                'neutral_percentage': 0,
                'negative_percentage': 0,
                'total_mentions': 0,
                'themes': []
            })
        
        # Calculate weighted percentages
        weighted_positive = sum(
            (item.positive_percentage * item.mention_count) for item in queryset
        ) / total_mentions
        weighted_neutral = sum(
            (item.neutral_percentage * item.mention_count) for item in queryset
        ) / total_mentions
        weighted_negative = sum(
            (item.negative_percentage * item.mention_count) for item in queryset
        ) / total_mentions
        
        # Get top themes
        themes = queryset.values('theme').annotate(
            total_mentions=Sum('mention_count')
        ).order_by('-total_mentions')[:5]
        
        return Response({
            'positive_percentage': round(weighted_positive, 2),
            'neutral_percentage': round(weighted_neutral, 2),
            'negative_percentage': round(weighted_negative, 2),
            'total_mentions': total_mentions,
            'themes': list(themes)
        })


class ShareOfVoiceAnalyticsViewSet(viewsets.ModelViewSet):
    serializer_class = ShareOfVoiceAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return ShareOfVoiceAnalytics.objects.all()
        return ShareOfVoiceAnalytics.objects.filter(domain__organisation=user.organisation)
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get share of voice for a specific domain."""
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))
        platform = request.query_params.get('platform')
        
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_date = timezone.now().date() - timedelta(days=days)
        queryset = self.get_queryset().filter(
            domain_id=domain_id,
            timestamp__gte=start_date
        )
        
        if platform:
            queryset = queryset.filter(platform=platform)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def comparison(self, request):
        """Get market share comparison for a domain."""
        domain_id = request.query_params.get('domain_id')
        date = request.query_params.get('date', timezone.now().date())
        platform = request.query_params.get('platform')
        
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            domain_id=domain_id,
            timestamp=date
        )
        
        if platform:
            queryset = queryset.filter(platform=platform)
        else:
            queryset = queryset.filter(platform__isnull=True)  # Overall data
        
        # Separate your brand vs competitors
        your_data = queryset.filter(competitor__isnull=True).first()
        competitors_data = queryset.filter(competitor__isnull=False).order_by('market_position')
        
        return Response({
            'your_brand': ShareOfVoiceAnalyticsSerializer(your_data).data if your_data else None,
            'competitors': ShareOfVoiceAnalyticsSerializer(competitors_data, many=True).data,
            'total_market_mentions': queryset.aggregate(Sum('mention_count'))['mention_count__sum'] or 0
        })

