from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Avg, Count, Q, F, Max, Min
from django.shortcuts import get_object_or_404
from collections import defaultdict
from datetime import timedelta
from django.utils import timezone
from .models import Competitor, CompetitorAnalytics, CompetitorPrompt, CompetitorPromptAnalytics, CompetitorMetricSnapshot, CompetitiveInsight
from domains.models import Domain
from prompts.models import PromptAnalytics
from analytics.models import ShareOfVoiceAnalytics
from .serializers import (
    CompetitorSerializer, CompetitorAnalyticsSerializer, CompetitorPromptSerializer,
    CompetitorPromptAnalyticsSerializer, CompetitorMetricSnapshotSerializer,
    CompetitiveInsightSerializer
)


class CompetitorViewSet(viewsets.ModelViewSet):
    serializer_class = CompetitorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Competitor.objects.all() if user.role == 'super_admin' else Competitor.objects.filter(domain__organisation=user.organisation)

        # Filter by domain_id if provided in query params
        domain_id = self.request.query_params.get('domain_id')
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get competitors for a specific domain with optional platform filtering."""
        domain_id = request.query_params.get('domain_id')
        platform = request.query_params.get('platform')  # NEW: Platform filter

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        competitors = self.get_queryset().filter(domain_id=domain_id)

        # If platform filter is specified and not 'all', calculate metrics from analytics
        if platform and platform.lower() != 'all':
            result = []
            for comp in competitors:
                # Filter analytics by platform
                analytics_filter = Q(competitor=comp, platform__iexact=platform)
                comp_analytics = CompetitorPromptAnalytics.objects.filter(analytics_filter)

                # Calculate platform-specific metrics
                total_mentions = comp_analytics.filter(is_mentioned=True).aggregate(
                    total=Sum('mention_count')
                )['total'] or 0

                total_citations = 0
                for ca in comp_analytics.filter(is_mentioned=True):
                    if ca.citation_list and isinstance(ca.citation_list, list):
                        total_citations += len(ca.citation_list)

                avg_position = comp_analytics.filter(is_mentioned=True, position__isnull=False).aggregate(
                    avg=Avg('position')
                )['avg'] or 0

                avg_sentiment = comp_analytics.filter(is_mentioned=True, sentiment_score__isnull=False).aggregate(
                    avg=Avg('sentiment_score')
                )['avg'] or 0

                # Calculate visibility score (100 - position * 20, capped at 0-100)
                visibility = 100.0 - (float(avg_position) * 20.0) if avg_position > 0 else 0.0
                visibility = max(0.0, min(100.0, visibility))

                # Get share of voice for this platform
                from analytics.models import ShareOfVoiceAnalytics
                sov = ShareOfVoiceAnalytics.objects.filter(
                    competitor=comp,
                    platform__iexact=platform
                ).order_by('-timestamp').first()
                share_of_voice = float(sov.share_percentage) if sov else 0.0

                # Build response matching serializer format
                result.append({
                    'id': comp.id,
                    'domain': comp.domain_id,
                    'domain_name': comp.domain.name,
                    'name': comp.name,
                    'url': comp.url,
                    'track_status': comp.track_status,
                    'track_message': comp.track_message,
                    'tracked_at': comp.tracked_at,
                    'total_mentions': int(total_mentions),
                    'total_citations': total_citations,
                    'visibility_score': round(visibility, 2),
                    'sentiment_score': round(float(avg_sentiment), 2),
                    'average_position': round(float(avg_position), 2),
                    'share_of_voice_percentage': round(share_of_voice, 2),
                    'trend_percentage': 0.0,  # Trend not calculated for platform filter
                    'created_by': comp.created_by_id,
                    'created_by_email': comp.created_by.email if comp.created_by else None,
                    'created_at': comp.created_at,
                    'modified_at': comp.modified_at,
                })

            return Response(result)

        # No platform filter - return aggregated data
        queryset = self.get_queryset().filter(domain_id=domain_id)
        competitors_data = CompetitorSerializer(queryset, many=True).data
        for comp in competitors_data:
            comp['is_you'] = False  # Flag competitors
        
        # Get domain to include as "You"
        from domains.models import Domain
        from analytics.models import ShareOfVoiceAnalytics
        try:
            # Ensure user has access to this domain
            user = request.user
            if user.role == 'super_admin':
                domain = Domain.objects.get(id=domain_id)
            else:
                domain = Domain.objects.get(id=domain_id, organisation=user.organisation)
        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found or you do not have access to it'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get latest share of voice for "You"
        your_sov = ShareOfVoiceAnalytics.objects.filter(
            domain_id=domain_id,
            competitor__isnull=True
        ).order_by('-timestamp').first()
        
        # Build "You" entry
        you_entry = {
            'id': None,
            'domain': domain.id,
            'domain_name': domain.name,
            'name': 'You',
            'url': domain.url,
            'track_status': domain.processing_status,
            'track_message': domain.track_message,
            'tracked_at': domain.tracked_at.isoformat() if domain.tracked_at else None,
            'total_mentions': domain.total_mentions,
            'total_citations': domain.total_citations,
            'visibility_score': float(domain.visibility_score),
            'sentiment_score': float(domain.sentiment_score),
            'average_position': float(domain.average_position),
            'share_of_voice_percentage': float(your_sov.share_percentage) if your_sov else 0.0,
            'trend_percentage': 0.0,
            'created_by': None,
            'created_by_email': None,
            'created_at': domain.created_at.isoformat(),
            'modified_at': domain.modified_at.isoformat(),
            'is_you': True
        }
        
        # Return "You" first, then competitors
        return Response([you_entry] + competitors_data)
    
    @action(detail=False, methods=['get'])
    def comparison(self, request):
        """Get competitive comparison data, including 'You' (your domain) as first item."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get domain to include as "You"
        from domains.models import Domain
        from analytics.models import ShareOfVoiceAnalytics
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get latest share of voice for "You"
        your_sov = ShareOfVoiceAnalytics.objects.filter(
            domain_id=domain_id,
            competitor__isnull=True
        ).order_by('-timestamp').first()
        
        # Build "You" entry
        you_entry = {
            'id': None,
            'domain': domain.id,
            'domain_name': domain.name,
            'name': 'You',
            'url': domain.url,
            'track_status': domain.processing_status,
            'track_message': domain.track_message,
            'tracked_at': domain.tracked_at.isoformat() if domain.tracked_at else None,
            'total_mentions': domain.total_mentions,
            'visibility_score': float(domain.visibility_score),
            'sentiment_score': float(domain.sentiment_score),
            'average_position': float(domain.average_position),
            'share_of_voice_percentage': float(your_sov.share_percentage) if your_sov else 0.0,
            'trend_percentage': 0.0,
            'created_by': None,
            'created_by_email': None,
            'created_at': domain.created_at.isoformat(),
            'modified_at': domain.modified_at.isoformat(),
            'is_you': True
        }
        
        # Get competitors
        competitors = self.get_queryset().filter(domain_id=domain_id)
        competitors_data = CompetitorSerializer(competitors, many=True).data
        for comp in competitors_data:
            comp['is_you'] = False
        
        # Calculate summary including "You"
        all_mentions = [domain.total_mentions] + [c.total_mentions for c in competitors]
        total_market_mentions = sum(all_mentions)
        avg_mentions = sum(all_mentions) / len(all_mentions) if all_mentions else 0
        
        data = {
            'competitors': [you_entry] + competitors_data,  # "You" first
            'summary': {
                'total_competitors': competitors.count() + 1,  # Include "You"
                'avg_mentions': avg_mentions,
                'total_market_mentions': total_market_mentions,
            }
        }
        return Response(data)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """
        Get detailed analytics for a competitor (matches engine endpoint).
        Returns data in the same format as engine /api/competitors/{id}/analytics/
        """
        competitor = self.get_object()
        
        # Get competitor-prompt analytics
        prompt_analytics = CompetitorPromptAnalytics.objects.filter(
            competitor=competitor
        ).select_related('prompt')
        
        # Calculate statistics
        stats = prompt_analytics.aggregate(
            total_tested=Count('id'),
            total_mentioned=Count('id', filter=Q(is_mentioned=True)),
            avg_position=Avg('position'),
            avg_sentiment=Avg('sentiment_score'),
            total_mentions=Sum('mention_count')
        )
        
        mention_rate = 0
        if stats['total_tested'] and stats['total_tested'] > 0:
            mention_rate = (stats['total_mentioned'] / stats['total_tested']) * 100
        
        return Response({
            'competitor': CompetitorSerializer(competitor).data,
            'statistics': {
                'total_prompts_tested': stats['total_tested'] or 0,
                'times_mentioned': stats['total_mentioned'] or 0,
                'mention_rate': round(mention_rate, 2),
                'average_position': round(float(stats['avg_position'] or 0), 2),
                'average_sentiment': round(float(stats['avg_sentiment'] or 0), 2),
                'total_mention_count': stats['total_mentions'] or 0,
            },
            'recent_prompts': CompetitorPromptAnalyticsSerializer(
                prompt_analytics.order_by('-tracked_at')[:10], many=True
            ).data
        })


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


class CompetitorPromptAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing CompetitorPromptAnalytics.
    Read-only because these are auto-generated by the CompetitorProcessor.

    Supports query parameters:
    - domain_id: Filter by domain
    - competitor_id: Filter by competitor
    - is_mentioned: Filter only where competitor is mentioned (true/false)
    """
    serializer_class = CompetitorPromptAnalyticsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Base queryset with organization filter
        if user.role == 'super_admin':
            queryset = CompetitorPromptAnalytics.objects.all()
        else:
            queryset = CompetitorPromptAnalytics.objects.filter(
                competitor__domain__organisation=user.organisation
            )

        # Apply query parameter filters for better performance
        domain_id = self.request.query_params.get('domain_id')
        competitor_id = self.request.query_params.get('competitor_id')
        is_mentioned = self.request.query_params.get('is_mentioned')
        platform = self.request.query_params.get('platform')

        if domain_id:
            queryset = queryset.filter(competitor__domain_id=domain_id)

        if competitor_id:
            queryset = queryset.filter(competitor_id=competitor_id)

        if platform:
            queryset = queryset.filter(platform__iexact=platform)

        # Filter to only mentioned rows (most important for performance!)
        if is_mentioned and is_mentioned.lower() == 'true':
            queryset = queryset.filter(is_mentioned=True)

        # Optimize with select_related to avoid N+1 queries
        queryset = queryset.select_related('competitor', 'prompt')

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Override list to group by prompt and include domain's own mentions from PromptAnalytics.
        Returns prompts with nested analytics array containing all competitors + user's brand.
        """
        from prompts.models import PromptAnalytics, Prompt
        from collections import defaultdict

        domain_id = request.query_params.get('domain_id')
        competitor_id = request.query_params.get('competitor_id')
        is_mentioned = request.query_params.get('is_mentioned')
        platform = request.query_params.get('platform')

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=400)

        user = request.user

        # Get competitor data
        queryset = self.filter_queryset(self.get_queryset())
        competitor_analytics = queryset.select_related('prompt', 'competitor')

        # Get user's brand data from PromptAnalytics
        if user.role == 'super_admin':
            pa_queryset = PromptAnalytics.objects.filter(
                prompt__group__domain_id=domain_id
            )
        else:
            pa_queryset = PromptAnalytics.objects.filter(
                prompt__group__domain_id=domain_id,
                prompt__group__domain__organisation=user.organisation
            )

        # Apply platform filter if provided
        if platform:
            pa_queryset = pa_queryset.filter(platform__iexact=platform)

        # Apply is_mentioned filter if provided
        if is_mentioned:
            if is_mentioned.lower() == 'true':
                pa_queryset = pa_queryset.filter(is_mention=True)
            elif is_mentioned.lower() == 'false':
                pa_queryset = pa_queryset.filter(is_mention=False)

        pa_queryset = pa_queryset.select_related('prompt', 'prompt__group', 'prompt__group__domain')

        # Group all analytics by prompt_id
        prompt_groups = defaultdict(lambda: {
            'prompt_id': None,
            'prompt_text': '',
            'domain_name': '',
            'analytics': []
        })

        # Add competitor analytics to groups
        for cpa in competitor_analytics:
            prompt_id = cpa.prompt.id
            if not prompt_groups[prompt_id]['prompt_id']:
                prompt_groups[prompt_id]['prompt_id'] = prompt_id
                prompt_groups[prompt_id]['prompt_text'] = cpa.prompt.prompt
                prompt_groups[prompt_id]['domain_name'] = cpa.competitor.domain.name

            prompt_groups[prompt_id]['analytics'].append({
                'id': cpa.id,
                'competitor_id': cpa.competitor.id,
                'competitor_name': cpa.competitor.name,
                'track_status': cpa.track_status,
                'track_message': cpa.track_message,
                'tracked_at': cpa.tracked_at.isoformat() if cpa.tracked_at else None,
                'is_mentioned': cpa.is_mentioned,
                'position': float(cpa.position) if cpa.position else None,
                'mention_count': cpa.mention_count,
                'sentiment_category': cpa.sentiment_category,
                'sentiment_score': float(cpa.sentiment_score) if cpa.sentiment_score else 0.0,
                'platform': cpa.platform,
                'citation_list': cpa.citation_list if cpa.citation_list else [],
                'created_at': cpa.created_at.isoformat() if cpa.created_at else None,
                'modified_at': cpa.modified_at.isoformat() if cpa.modified_at else None,
            })

        # Add user's brand analytics to groups (if not filtering by specific competitor)
        if not competitor_id:
            for pa in pa_queryset:
                prompt_id = pa.prompt.id
                if not prompt_groups[prompt_id]['prompt_id']:
                    prompt_groups[prompt_id]['prompt_id'] = prompt_id
                    prompt_groups[prompt_id]['prompt_text'] = pa.prompt.prompt
                    prompt_groups[prompt_id]['domain_name'] = pa.prompt.group.domain.name

                prompt_groups[prompt_id]['analytics'].append({
                    'id': pa.id,
                    'competitor_id': None,
                    'competitor_name': None,  # Frontend will handle as "You"
                    'track_status': pa.track_status,
                    'track_message': pa.track_message,
                    'tracked_at': pa.tracked_at.isoformat() if pa.tracked_at else None,
                    'is_mentioned': pa.is_mention,
                    'position': float(pa.position) if pa.position else None,
                    'mention_count': pa.total_mentions,
                    'sentiment_category': pa.sentiment_category,
                    'sentiment_score': float(pa.sentiment_score) if pa.sentiment_score else 0.0,
                    'platform': pa.platform,
                    'citation_list': pa.citation_list if pa.citation_list else [],
                    'created_at': pa.created_at.isoformat() if pa.created_at else None,
                    'modified_at': pa.modified_at.isoformat() if pa.modified_at else None,
                })

        # Convert to list and sort by most recent tracked_at
        grouped_prompts = list(prompt_groups.values())

        # Sort by the most recent tracked_at in the analytics array
        def get_latest_tracked_at(prompt_group):
            tracked_dates = [a['tracked_at'] for a in prompt_group['analytics'] if a['tracked_at']]
            return max(tracked_dates) if tracked_dates else ''

        grouped_prompts.sort(key=get_latest_tracked_at, reverse=True)

        # Apply pagination at the PROMPT level
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        total_count = len(grouped_prompts)
        total_pages = (total_count + page_size - 1) // page_size
        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        paginated_prompts = grouped_prompts[start_index:end_index]

        return Response({
            'results': paginated_prompts,
            'count': total_count,
            'total_pages': total_pages,
            'current_page': page,
            'page_size': page_size,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        })
    
    @action(detail=False, methods=['get'])
    def by_competitor(self, request):
        """Get all prompt analytics for a specific competitor."""
        competitor_id = request.query_params.get('competitor_id')
        if not competitor_id:
            return Response(
                {'error': 'competitor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(competitor_id=competitor_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def gaps(self, request):
        """Get prompts where competitor appears but you don't (opportunity gaps)."""
        domain_id = request.query_params.get('domain_id')
        competitor_id = request.query_params.get('competitor_id')
        
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            competitor__domain_id=domain_id,
            is_mentioned=True,  # Competitor is mentioned
            position__lte=5  # In top 5
        )
        
        if competitor_id:
            queryset = queryset.filter(competitor_id=competitor_id)
        
        # TODO: Add filter for "your brand not mentioned" by joining with PromptAnalytics
        
        queryset = queryset.order_by('position')
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


class CompetitorMetricSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompetitorMetricSnapshotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = CompetitorMetricSnapshot.objects.all()
        if user.role != 'super_admin':
            queryset = queryset.filter(domain__organisation=user.organisation)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        domain_id = request.query_params.get('domain_id')
        competitor_id = request.query_params.get('competitor_id')
        platform = request.query_params.get('platform')  # NEW: Platform filter
        days = int(request.query_params.get('days', 90))

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        if competitor_id:
            queryset = queryset.filter(competitor_id=competitor_id)
        if days:
            queryset = queryset.filter(timestamp__gte=timezone.now() - timedelta(days=days))

        # NEW: Filter by platform if provided (and not 'all')
        if platform and platform.lower() != 'all':
            # Filter snapshots that have platform_metrics matching the specified platform
            from django.db.models import JSONField
            import json
            filtered_ids = []
            for snap in queryset:
                if snap.platform_metrics:
                    for metric in snap.platform_metrics:
                        if metric.get('platform', '').lower() == platform.lower():
                            filtered_ids.append(snap.id)
                            break
            queryset = queryset.filter(id__in=filtered_ids) if filtered_ids else queryset.none()

        queryset = queryset.order_by('-timestamp')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def competitive_strength_analysis(request):
    """
    Get competitive strength analysis data for radar chart.
    Returns metrics: Visibility, Sentiment, Position, Coverage, Growth
    """
    try:
        domain_id = request.GET.get('domain_id')
        platform = request.GET.get('platform')  # NEW: Platform filter
        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get top 3 competitors (by share of voice) plus your brand
        competitors = Competitor.objects.filter(domain_id=domain_id).order_by('-share_of_voice_percentage')[:3]
        
        # Get your brand data from domain
        from domains.models import Domain
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get your brand's prompt analytics
        your_prompts_filter = Q(prompt__group__domain_id=domain_id, is_mention=True)
        # NEW: Filter by platform if specified
        if platform and platform.lower() != 'all':
            your_prompts_filter &= Q(platform__iexact=platform)
        your_prompts = PromptAnalytics.objects.filter(your_prompts_filter)
        
        your_mentions = your_prompts.count()
        your_avg_position = float(your_prompts.aggregate(avg=Avg('position'))['avg'] or 0)
        your_sentiment = float(your_prompts.aggregate(avg=Avg('sentiment_score'))['avg'] or 0)
        your_visibility = 100.0 - (your_avg_position * 20.0) if your_avg_position > 0 else 0.0
        your_visibility = max(0.0, min(100.0, your_visibility))
        
        # Calculate coverage (percentage of prompts where mentioned)
        total_prompts = your_prompts.values('prompt').distinct().count()
        your_coverage = (your_mentions / total_prompts * 100) if total_prompts > 0 else 0
        
        # Calculate growth (compare last 30 days vs previous 30 days)
        from datetime import date, datetime
        today = timezone.now().date()
        last_30_days = your_prompts.filter(created_at__gte=timezone.now() - timedelta(days=30))
        prev_30_days = your_prompts.filter(
            created_at__gte=timezone.now() - timedelta(days=60),
            created_at__lt=timezone.now() - timedelta(days=30)
        )
        last_count = last_30_days.count()
        prev_count = prev_30_days.count()
        your_growth = ((last_count - prev_count) / prev_count * 100) if prev_count > 0 else 0
        
        # Build metrics array
        metrics = []
        
        # Normalize brand names for frontend
        # Use "You" for your brand, normalize competitor names
        def normalize_brand_name(name):
            return name.lower().replace(' ', '').replace('-', '').replace('_', '')
        
        # Visibility metric
        visibility_data = {'metric': 'Visibility'}
        visibility_data['you'] = round(your_visibility, 0)  # Use "you" as key for your brand
        for idx, comp in enumerate(competitors):
            comp_name = normalize_brand_name(comp.name)
            visibility_data[comp_name] = round(float(comp.visibility_score or 0), 0)
        metrics.append(visibility_data)
        
        # Sentiment metric
        sentiment_data = {'metric': 'Sentiment'}
        sentiment_data['you'] = round(your_sentiment * 100, 0) if your_sentiment else 0
        for idx, comp in enumerate(competitors):
            comp_name = normalize_brand_name(comp.name)
            sentiment_data[comp_name] = round(float(comp.sentiment_score or 0) * 100, 0)
        metrics.append(sentiment_data)
        
        # Position metric (inverted - lower is better, so we convert to score)
        position_data = {'metric': 'Position'}
        position_score = 100.0 - (your_avg_position * 10.0) if your_avg_position > 0 else 0.0
        position_score = max(0.0, min(100.0, position_score))
        position_data['you'] = round(position_score, 0)
        for idx, comp in enumerate(competitors):
            comp_name = normalize_brand_name(comp.name)
            comp_pos_score = 100.0 - (float(comp.average_position or 0) * 10.0)
            comp_pos_score = max(0.0, min(100.0, comp_pos_score))
            position_data[comp_name] = round(comp_pos_score, 0)
        metrics.append(position_data)
        
        # Coverage metric
        coverage_data = {'metric': 'Coverage'}
        coverage_data['you'] = round(your_coverage, 0)
        # For competitors, calculate coverage from CompetitorPromptAnalytics
        for idx, comp in enumerate(competitors):
            comp_name = normalize_brand_name(comp.name)
            comp_analytics_filter = Q(competitor=comp, is_mentioned=True)
            # NEW: Filter by platform if specified
            if platform and platform.lower() != 'all':
                comp_analytics_filter &= Q(platform__iexact=platform)
            comp_analytics = CompetitorPromptAnalytics.objects.filter(comp_analytics_filter)
            comp_total_prompts = comp_analytics.values('prompt').distinct().count()
            comp_mentioned = comp_analytics.count()
            comp_coverage = (comp_mentioned / comp_total_prompts * 100) if comp_total_prompts > 0 else 0
            coverage_data[comp_name] = round(comp_coverage, 0)
        metrics.append(coverage_data)
        
        # Growth metric
        growth_data = {'metric': 'Growth'}
        growth_data['you'] = round(your_growth, 0)
        # For competitors, calculate growth from CompetitorAnalytics
        for idx, comp in enumerate(competitors):
            comp_name = normalize_brand_name(comp.name)
            comp_analytics_filter = Q(competitor=comp)
            # NEW: Filter by platform if specified
            if platform and platform.lower() != 'all':
                comp_analytics_filter &= Q(platform__iexact=platform)
            comp_analytics = CompetitorAnalytics.objects.filter(comp_analytics_filter)
            last_30 = comp_analytics.filter(timestamp__gte=today - timedelta(days=30))
            prev_30 = comp_analytics.filter(
                timestamp__gte=today - timedelta(days=60),
                timestamp__lt=today - timedelta(days=30)
            )
            last_sum = last_30.aggregate(Sum('total_mentions'))['total_mentions__sum'] or 0
            prev_sum = prev_30.aggregate(Sum('total_mentions'))['total_mentions__sum'] or 0
            comp_growth = ((last_sum - prev_sum) / prev_sum * 100) if prev_sum > 0 else 0
            growth_data[comp_name] = round(comp_growth, 0)
        metrics.append(growth_data)
        
        return Response(metrics)
        
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in competitive_strength_analysis: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {'error': f'Failed to retrieve competitive strength analysis: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def competitive_insights(request):
    """
    Get automated competitive intelligence insights.
    Analyzes data to generate actionable insights.
    """
    try:
        domain_id = request.GET.get('domain_id')
        platform = request.GET.get('platform')  # NEW: Platform filter
        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from domains.models import Domain
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)
        
        stored_insights_qs = CompetitiveInsight.objects.filter(domain=domain).order_by('-generated_at')
        if stored_insights_qs.exists():
            serializer = CompetitiveInsightSerializer(stored_insights_qs[:2], many=True)
            return Response(serializer.data)
        
        insights = []
        
        # Get competitors ordered by share of voice
        competitors = Competitor.objects.filter(domain_id=domain_id).order_by('-share_of_voice_percentage')
        
        if not competitors.exists():
            return Response(insights)
        
        # Get your brand's metrics
        your_prompts_filter = Q(prompt__group__domain_id=domain_id, is_mention=True)
        # NEW: Filter by platform if specified
        if platform and platform.lower() != 'all':
            your_prompts_filter &= Q(platform__iexact=platform)
        your_prompts = PromptAnalytics.objects.filter(your_prompts_filter)
        your_mentions = your_prompts.count()

        your_sov_filter = Q(domain_id=domain_id, competitor__isnull=True)
        # NEW: Filter by platform if specified
        if platform and platform.lower() != 'all':
            your_sov_filter &= Q(platform__iexact=platform)
        your_sov = ShareOfVoiceAnalytics.objects.filter(your_sov_filter).order_by('-timestamp').first()
        your_sov_pct = float(your_sov.share_percentage) if your_sov else 0
        
        # Get top competitor
        top_competitor = competitors.first()
        
        # Insight 1: Market Leadership
        if your_sov_pct > 0 and top_competitor:
            top_comp_sov = float(top_competitor.share_of_voice_percentage or 0)
            if your_sov_pct > top_comp_sov:
                lead = your_sov_pct - top_comp_sov
                insights.append({
                    'title': 'Market Leadership Maintained',
                    'description': f'{domain.name} maintains #1 position with {your_sov_pct:.0f}% market share, {lead:.0f}% ahead of nearest competitor',
                    'type': 'success',
                    'impact': 'high'
                })
            elif top_comp_sov > your_sov_pct:
                gap = top_comp_sov - your_sov_pct
                insights.append({
                    'title': f'{top_competitor.name} Leading Market',
                    'description': f'{top_competitor.name} leads with {top_comp_sov:.0f}% share, {gap:.0f}% ahead of {domain.name}',
                    'type': 'warning',
                    'impact': 'high'
                })
        
        # Insight 2: Sentiment Advantage
        your_sentiment = float(your_prompts.aggregate(avg=Avg('sentiment_score'))['avg'] or 0) * 100
        for comp in competitors[:2]:  # Compare with top 2 competitors
            comp_sentiment = float(comp.sentiment_score or 0) * 100
            if your_sentiment > comp_sentiment + 5:  # 5% advantage
                diff = your_sentiment - comp_sentiment
                insights.append({
                    'title': 'Sentiment Advantage',
                    'description': f'{diff:.0f}% higher positive sentiment than {comp.name}, driven by quality mentions',
                    'type': 'success',
                    'impact': 'medium'
                })
                break
        
        # Insight 3: Competitor Momentum
        from datetime import date
        today = date.today()
        for comp in competitors[:2]:
            comp_analytics_filter = Q(competitor=comp)
            # NEW: Filter by platform if specified
            if platform and platform.lower() != 'all':
                comp_analytics_filter &= Q(platform__iexact=platform)
            comp_analytics = CompetitorAnalytics.objects.filter(comp_analytics_filter)
            last_30 = comp_analytics.filter(timestamp__gte=today - timedelta(days=30))
            prev_30 = comp_analytics.filter(
                timestamp__gte=today - timedelta(days=60),
                timestamp__lt=today - timedelta(days=30)
            )
            last_sum = last_30.aggregate(Sum('total_mentions'))['total_mentions__sum'] or 0
            prev_sum = prev_30.aggregate(Sum('total_mentions'))['total_mentions__sum'] or 0
            if prev_sum > 0:
                growth = ((last_sum - prev_sum) / prev_sum * 100)
                if growth > 5:  # 5% growth
                    insights.append({
                        'title': f'{comp.name} Gaining Momentum',
                        'description': f'{comp.name} increased mentions by {growth:.0f}% this month, focused on market positioning',
                        'type': 'warning',
                        'impact': 'medium'
                    })
                    break
        
        # Insight 4: Opportunity Gaps
        # Find prompts where competitors are mentioned but you're not
        comp_gap_filter = Q(competitor__domain_id=domain_id, is_mentioned=True, position__lte=5)
        # NEW: Filter by platform if specified
        if platform and platform.lower() != 'all':
            comp_gap_filter &= Q(platform__iexact=platform)
        comp_mentioned_prompts = CompetitorPromptAnalytics.objects.filter(comp_gap_filter).values_list('prompt_id', flat=True).distinct()

        your_mentioned_prompts = your_prompts.values_list('prompt_id', flat=True).distinct()
        gap_prompts = set(comp_mentioned_prompts) - set(your_mentioned_prompts)
        
        if len(gap_prompts) > 0:
            # Find category with most gaps
            from prompts.models import Prompt
            gap_prompt_objs = Prompt.objects.filter(id__in=list(gap_prompts)[:10])
            if gap_prompt_objs.exists():
                insights.append({
                    'title': 'Opportunity in Content Gaps',
                    'description': f'Found {len(gap_prompts)} prompts where competitors appear but {domain.name} doesn\'t - opportunity to increase presence',
                    'type': 'opportunity',
                    'impact': 'high'
                })
        
        return Response(insights[:2])  # Return top 2 insights
        
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in competitive_insights: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {'error': f'Failed to retrieve competitive insights: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def answer_gap_analysis(request):
    """
    Get answer gap analysis - queries where competitors appear but you don't.
    """
    try:
        domain_id = request.GET.get('domain_id')
        competitor_id = request.GET.get('competitor_id')
        platform = request.GET.get('platform')  # NEW: Platform filter

        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get your brand's mentioned prompts
        your_prompts_filter = Q(prompt__group__domain_id=domain_id, is_mention=True)
        # NEW: Filter by platform if specified
        if platform and platform.lower() != 'all':
            your_prompts_filter &= Q(platform__iexact=platform)
        your_mentioned_prompts = PromptAnalytics.objects.filter(your_prompts_filter).values_list('prompt_id', flat=True).distinct()

        # Get competitor mentioned prompts
        comp_filter = Q(competitor__domain_id=domain_id, is_mentioned=True, position__lte=10)
        if competitor_id:
            comp_filter &= Q(competitor_id=competitor_id)
        # NEW: Filter by platform if specified
        if platform and platform.lower() != 'all':
            comp_filter &= Q(platform__iexact=platform)
        
        comp_analytics = CompetitorPromptAnalytics.objects.filter(comp_filter).select_related(
            'competitor', 'prompt'
        )
        
        # Find gaps - prompts where competitor is mentioned but you're not
        gaps = []
        processed_prompts = set()
        
        for comp_anal in comp_analytics:
            prompt_id = comp_anal.prompt_id
            if prompt_id in processed_prompts or prompt_id in your_mentioned_prompts:
                continue
            
            processed_prompts.add(prompt_id)
            
            # Get all competitor mentions for this prompt
            all_comp_filter = Q(prompt_id=prompt_id, competitor__domain_id=domain_id, is_mentioned=True)
            # NEW: Filter by platform if specified
            if platform and platform.lower() != 'all':
                all_comp_filter &= Q(platform__iexact=platform)
            all_comp_mentions = CompetitorPromptAnalytics.objects.filter(all_comp_filter)

            # Get your mentions for this prompt
            your_count_filter = Q(prompt_id=prompt_id, prompt__group__domain_id=domain_id, is_mention=True)
            # NEW: Filter by platform if specified
            if platform and platform.lower() != 'all':
                your_count_filter &= Q(platform__iexact=platform)
            your_mentions_count = PromptAnalytics.objects.filter(your_count_filter).count()
            
            # Find which competitor has most mentions
            comp_mentions_by_comp = {}
            platforms_set = set()
            for c in all_comp_mentions:
                comp_name = c.competitor.name
                if comp_name not in comp_mentions_by_comp:
                    comp_mentions_by_comp[comp_name] = 0
                comp_mentions_by_comp[comp_name] += c.mention_count
                if c.platform:
                    platforms_set.add(c.platform)
            
            if comp_mentions_by_comp:
                top_competitor = max(comp_mentions_by_comp.items(), key=lambda x: x[1])
                total_comp_mentions = sum(comp_mentions_by_comp.values())
                
                # Determine opportunity level
                if total_comp_mentions >= 50 and your_mentions_count == 0:
                    opportunity = 'high'
                elif total_comp_mentions >= 30 and your_mentions_count < 5:
                    opportunity = 'medium'
                else:
                    opportunity = 'low'
                
                gaps.append({
                    'id': len(gaps) + 1,
                    'query': comp_anal.prompt.prompt,
                    'competitor': top_competitor[0],
                    'mentions': total_comp_mentions,
                    'yourMentions': your_mentions_count,
                    'opportunity': opportunity,
                    'platforms': list(platforms_set) if platforms_set else ['ChatGPT', 'Perplexity']
                })
        
        # Sort by opportunity and mentions
        gaps.sort(key=lambda x: (x['opportunity'] == 'high', x['mentions']), reverse=True)
        
        return Response(gaps[:20])  # Return top 20 gaps
        
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in answer_gap_analysis: {str(e)}\n{traceback.format_exc()}")
        return Response(
            {'error': f'Failed to retrieve answer gap analysis: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def competitor_heatmap(request):
    try:
        domain_id = request.GET.get('domain_id')
        platform = request.GET.get('platform')  # NEW: Platform filter
        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        days = int(request.GET.get('days', 90))
        since = timezone.now() - timedelta(days=days)

        snapshots = CompetitorMetricSnapshot.objects.filter(
            domain_id=domain_id,
            timestamp__gte=since
        ).select_related('competitor', 'domain').order_by('-timestamp')

        domain = Domain.objects.filter(id=domain_id).only('id', 'name', 'url').first()

        latest_snapshots = []
        seen = set()
        for snap in snapshots:
            key = snap.competitor_id or f"domain-{snap.domain_id}"
            if key in seen:
                continue
            latest_snapshots.append(snap)
            seen.add(key)

        rows = []
        platform_totals = defaultdict(float)

        for snap in latest_snapshots:
            metrics = snap.platform_metrics or []
            platform_mentions = {}
            for metric in metrics:
                platform_name = metric.get('platform') or 'Overall'
                # NEW: Filter by platform if specified
                if platform and platform.lower() != 'all':
                    if platform_name.lower() != platform.lower():
                        continue
                mentions = float(metric.get('mentions') or 0)
                if mentions <= 0:
                    continue
                platform_mentions[platform_name] = mentions
                platform_totals[platform_name] += mentions

            if not platform_mentions:
                continue

            rows.append({
                'name': snap.competitor.name if snap.competitor else snap.domain.name,
                'isYou': snap.competitor is None,
                'platform_mentions': platform_mentions,
                'url': (snap.competitor.url if snap.competitor else snap.domain.url) if snap.competitor or snap.domain else None,
            })

        if not any(row['isYou'] for row in rows):
            your_platforms = defaultdict(float)
            sov_filter = Q(domain_id=domain_id, competitor__isnull=True, timestamp__gte=since)
            # NEW: Filter by platform if specified
            if platform and platform.lower() != 'all':
                sov_filter &= Q(platform__iexact=platform)
            sov_records = ShareOfVoiceAnalytics.objects.filter(sov_filter)
            for record in sov_records:
                plat_name = record.platform or 'Overall'
                mentions = float(record.mention_count or 0)
                if mentions <= 0:
                    continue
                your_platforms[plat_name] += mentions
                platform_totals[plat_name] += mentions
            if your_platforms:
                rows.append({
                    'name': 'Your Brand',
                    'isYou': True,
                    'platform_mentions': dict(your_platforms),
                    'url': domain.url if domain else None,
                })

        platforms = sorted(platform_totals.keys())
        formatted_rows = []
        for row in rows:
            percentages = {}
            for platform in platforms:
                mentions = row['platform_mentions'].get(platform, 0)
                total = platform_totals.get(platform) or 1
                percentages[platform] = round((mentions / total) * 100, 2)
            formatted_rows.append({
                'name': row['name'],
                'isYou': row['isYou'],
                'platforms': percentages,
                'url': row.get('url') or (domain.url if row['isYou'] and domain else None),
            })

        return Response({'platforms': platforms, 'rows': formatted_rows})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_competitor_single(request):
    """
    Process a single competitor by competitor_id from request body.
    Similar to engine's /api/competitors/process-single/ endpoint.
    
    Request body:
    {
        "competitor_id": 123,
        "sync": true  // optional, defaults to true
    }
    """
    import logging
    import requests
    from django.conf import settings
    
    logger = logging.getLogger(__name__)
    
    try:
        competitor_id = request.data.get('competitor_id')
        if not competitor_id:
            return Response(
                {'error': 'competitor_id is required in request body'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get competitor
        competitor = get_object_or_404(Competitor, id=competitor_id)
        
        # Check if user has access to this competitor's domain
        user = request.user
        if user.role != 'super_admin' and competitor.domain.organisation != user.organisation:
            return Response(
                {'error': 'You do not have permission to process this competitor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check competitor status
        if competitor.track_status not in ['INIT', 'FAIL', 'COMP']:
            return Response(
                {
                    'error': f'Competitor is already in status {competitor.track_status}. Cannot process.',
                    'current_status': competitor.track_status
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Always process synchronously to complete the full process
        engine_api_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001')
        sync = request.data.get('sync', True)  # Default to sync for complete processing
        
        try:
            # Call engine API - always use sync=True for complete processing
            engine_endpoint = f"{engine_api_url}/api/competitors/process-single/"
            response = requests.post(
                engine_endpoint,
                json={
                    'competitor_id': competitor_id,
                    'sync': True  # Always sync for complete processing
                },
                headers={'Content-Type': 'application/json'},
                timeout=600  # 10 minutes timeout for complete processing
            )
            
            if response.status_code == 200:
                result = response.json()
                return Response({
                    'success': True,
                    'message': 'Competitor processing completed successfully',
                    'competitor_id': competitor_id,
                    'competitor_name': competitor.name,
                    'mode': 'engine_api',
                    **result
                }, status=status.HTTP_200_OK)
            else:
                error_data = response.json() if response.content else {'error': 'Unknown error'}
                return Response({
                    'success': False,
                    'error': error_data.get('error', 'Engine API returned an error'),
                    'engine_status_code': response.status_code
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except requests.exceptions.ConnectionError:
            # Engine not available, try to use processor directly if accessible
            logger.warning(f"Engine API not available at {engine_api_url}, trying direct processor import")
            
            try:
                # Try to import and use processor directly
                import sys
                import os
                # Add engine path if not already there
                engine_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'engine')
                if engine_path not in sys.path:
                    sys.path.insert(0, engine_path)
                
                from core.competitor_processor import CompetitorProcessor
                
                processor = CompetitorProcessor(
                    max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10)
                )
                
                # Use process_competitor which properly orchestrates the entire flow
                result = processor.process_competitor(competitor)
                
                competitor.refresh_from_db()
                
                if result.get('scheduled') and result.get('status') == 'completed':
                    return Response({
                        'success': True,
                        'message': f'Competitor processing completed for {competitor.name}',
                        'competitor_id': competitor_id,
                        'competitor_name': competitor.name,
                        'mode': 'direct_processor',
                        'track_status': competitor.track_status,
                        'track_message': competitor.track_message,
                        'processed': result.get('processed', 0),
                        'failed': result.get('failed', 0),
                        'total': result.get('total', 0),
                        'total_mentions': competitor.total_mentions,
                        'average_position': str(competitor.average_position),
                        'sentiment_score': str(competitor.sentiment_score),
                        'visibility_score': str(competitor.visibility_score),
                        'share_of_voice_percentage': str(competitor.share_of_voice_percentage)
                    }, status=status.HTTP_200_OK)
                else:
                    # Processing failed or was not scheduled
                    return Response({
                        'success': False,
                        'error': result.get('error', 'Processing failed'),
                        'reason': result.get('reason', 'unknown'),
                        'mode': 'direct_processor',
                        'track_status': competitor.track_status,
                        'track_message': competitor.track_message
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            except ImportError as import_error:
                logger.error(f"Failed to import processor: {str(import_error)}")
                return Response({
                    'success': False,
                    'error': 'Engine API is not available and processor cannot be imported directly. Please ensure the engine is running.',
                    'engine_url': engine_api_url,
                    'import_error': str(import_error)
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception as proc_error:
                logger.error(f"Error in direct processor: {str(proc_error)}")
                # Mark as failed
                try:
                    with transaction.atomic():
                        comp = Competitor.objects.select_for_update().get(id=competitor_id)
                        comp.track_status = 'FAIL'
                        comp.track_message = f"Processing failed: {str(proc_error)}"
                        comp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                except:
                    pass
                
                return Response({
                    'success': False,
                    'error': str(proc_error),
                    'mode': 'direct_processor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Competitor.DoesNotExist:
        return Response(
            {'error': f'Competitor with id {competitor_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error processing competitor {competitor_id}: {str(e)}")
        return Response(
            {'error': f'Failed to process competitor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_competitor_analysis(request):
    """
    Extract competitors from prompt analytics data and start processing them.
    This endpoint:
    1. Extracts top 5 competitors from existing prompt analytics
    2. Creates Competitor records
    3. Queues them for processing

    Request body:
    {
        "domain_id": 123
    }
    """
    import logging
    from .services import CompetitorExtractionService

    logger = logging.getLogger(__name__)

    try:
        domain_id = request.data.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required in request body'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get domain
        domain = get_object_or_404(Domain, id=domain_id)

        # Check if user has access to this domain
        user = request.user
        if user.role != 'super_admin' and domain.organisation != user.organisation:
            return Response(
                {'error': 'You do not have permission to analyze competitors for this domain'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Extract competitors for THIS domain only
        logger.info(f"Starting competitor extraction for domain {domain.id}: {domain.name}")
        service = CompetitorExtractionService(domain)
        created_count, competitor_names = service.extract_and_create_competitors()

        # Get all competitors for THIS domain only (including newly created)
        competitors = Competitor.objects.filter(domain_id=domain_id)
        logger.info(f"Found {competitors.count()} total competitors for domain {domain.id}")

        return Response({
            'success': True,
            'message': f'Successfully extracted {created_count} competitors',
            'created_count': created_count,
            'competitor_names': competitor_names,
            'total_competitors': competitors.count(),
            'competitors': CompetitorSerializer(competitors, many=True).data
        }, status=status.HTTP_200_OK)

    except Domain.DoesNotExist:
        return Response(
            {'error': f'Domain with id {domain_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error starting competitor analysis for domain {domain_id}: {str(e)}")
        return Response(
            {'error': f'Failed to start competitor analysis: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_competitor(request, competitor_id):
    """
    Process a competitor by triggering the engine processor.
    Similar to prompt processing endpoints.
    
    This endpoint can work in two modes:
    1. If engine is accessible, it calls the engine API
    2. Otherwise, it can import and use the processor directly (if code is accessible)
    """
    import logging
    import requests
    from django.conf import settings
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get competitor
        competitor = get_object_or_404(Competitor, id=competitor_id)
        
        # Check if user has access to this competitor's domain
        user = request.user
        if user.role != 'super_admin' and competitor.domain.organisation != user.organisation:
            return Response(
                {'error': 'You do not have permission to process this competitor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check competitor status
        if competitor.track_status not in ['INIT', 'FAIL', 'COMP']:
            return Response(
                {
                    'error': f'Competitor is already in status {competitor.track_status}. Cannot process.',
                    'current_status': competitor.track_status
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Always process synchronously to complete the full process
        engine_api_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001')
        sync = request.data.get('sync', True)  # Default to sync for complete processing
        
        try:
            # Call engine API - always use sync=True for complete processing
            engine_endpoint = f"{engine_api_url}/api/competitors/process-single/"
            response = requests.post(
                engine_endpoint,
                json={
                    'competitor_id': competitor_id,
                    'sync': True  # Always sync for complete processing
                },
                headers={'Content-Type': 'application/json'},
                timeout=600  # 10 minutes timeout for complete processing
            )
            
            if response.status_code == 200:
                result = response.json()
                return Response({
                    'success': True,
                    'message': 'Competitor processing completed successfully',
                    'competitor_id': competitor_id,
                    'competitor_name': competitor.name,
                    'mode': 'engine_api',
                    **result
                }, status=status.HTTP_200_OK)
            else:
                error_data = response.json() if response.content else {'error': 'Unknown error'}
                return Response({
                    'success': False,
                    'error': error_data.get('error', 'Engine API returned an error'),
                    'engine_status_code': response.status_code
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except requests.exceptions.ConnectionError:
            # Engine not available, try to use processor directly if accessible
            logger.warning(f"Engine API not available at {engine_api_url}, trying direct processor import")
            
            try:
                # Try to import and use processor directly
                import sys
                import os
                # Add engine path if not already there
                engine_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'engine')
                if engine_path not in sys.path:
                    sys.path.insert(0, engine_path)
                
                from core.competitor_processor import CompetitorProcessor
                
                processor = CompetitorProcessor(
                    max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10)
                )
                
                # Use process_competitor which properly orchestrates the entire flow
                result = processor.process_competitor(competitor)
                
                competitor.refresh_from_db()
                
                if result.get('scheduled') and result.get('status') == 'completed':
                    return Response({
                        'success': True,
                        'message': f'Competitor processing completed for {competitor.name}',
                        'competitor_id': competitor_id,
                        'competitor_name': competitor.name,
                        'mode': 'direct_processor',
                        'track_status': competitor.track_status,
                        'track_message': competitor.track_message,
                        'processed': result.get('processed', 0),
                        'failed': result.get('failed', 0),
                        'total': result.get('total', 0),
                        'total_mentions': competitor.total_mentions,
                        'average_position': str(competitor.average_position),
                        'sentiment_score': str(competitor.sentiment_score),
                        'visibility_score': str(competitor.visibility_score),
                        'share_of_voice_percentage': str(competitor.share_of_voice_percentage)
                    }, status=status.HTTP_200_OK)
                else:
                    # Processing failed or was not scheduled
                    return Response({
                        'success': False,
                        'error': result.get('error', 'Processing failed'),
                        'reason': result.get('reason', 'unknown'),
                        'mode': 'direct_processor',
                        'track_status': competitor.track_status,
                        'track_message': competitor.track_message
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            except ImportError as import_error:
                logger.error(f"Failed to import processor: {str(import_error)}")
                return Response({
                    'success': False,
                    'error': 'Engine API is not available and processor cannot be imported directly. Please ensure the engine is running.',
                    'engine_url': engine_api_url,
                    'import_error': str(import_error)
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception as proc_error:
                logger.error(f"Error in direct processor: {str(proc_error)}")
                # Mark as failed
                try:
                    with transaction.atomic():
                        comp = Competitor.objects.select_for_update().get(id=competitor_id)
                        comp.track_status = 'FAIL'
                        comp.track_message = f"Processing failed: {str(proc_error)}"
                        comp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                except:
                    pass
                
                return Response({
                    'success': False,
                    'error': str(proc_error),
                    'mode': 'direct_processor'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Competitor.DoesNotExist:
        return Response(
            {'error': f'Competitor with id {competitor_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error processing competitor {competitor_id}: {str(e)}")
        return Response(
            {'error': f'Failed to process competitor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

