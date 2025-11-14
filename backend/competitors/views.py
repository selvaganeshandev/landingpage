from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Avg, Count, Q, F, Max, Min
from django.shortcuts import get_object_or_404
from datetime import timedelta
from django.utils import timezone
from .models import Competitor, CompetitorAnalytics, CompetitorPrompt, CompetitorPromptAnalytics
from prompts.models import PromptAnalytics
from analytics.models import ShareOfVoiceAnalytics
from .serializers import (
    CompetitorSerializer, CompetitorAnalyticsSerializer, CompetitorPromptSerializer,
    CompetitorPromptAnalyticsSerializer
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
        """Get competitors for a specific domain, including 'You' (your domain) as first item."""
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
            'id': None,  # No competitor ID for "You"
            'domain': domain.id,
            'domain_name': domain.name,
            'name': 'You',  # Label as "You"
            'url': domain.url,
            'track_status': domain.processing_status,
            'track_message': domain.track_message,
            'tracked_at': domain.tracked_at.isoformat() if domain.tracked_at else None,
            'total_mentions': domain.total_mentions,
            'visibility_score': float(domain.visibility_score),
            'sentiment_score': float(domain.sentiment_score),
            'average_position': float(domain.average_position),
            'share_of_voice_percentage': float(your_sov.share_percentage) if your_sov else 0.0,
            'trend_percentage': 0.0,  # Can be calculated if needed
            'created_by': None,
            'created_by_email': None,
            'created_at': domain.created_at.isoformat(),
            'modified_at': domain.modified_at.isoformat(),
            'is_you': True  # Flag to identify "You" in frontend
        }
        
        # Get competitors
        queryset = self.get_queryset().filter(domain_id=domain_id)
        competitors_data = CompetitorSerializer(queryset, many=True).data
        for comp in competitors_data:
            comp['is_you'] = False  # Flag competitors
        
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
    """
    serializer_class = CompetitorPromptAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return CompetitorPromptAnalytics.objects.all()
        return CompetitorPromptAnalytics.objects.filter(
            competitor__domain__organisation=user.organisation
        )
    
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


@api_view(['GET'])
@permission_classes([AllowAny])
def competitive_strength_analysis(request):
    """
    Get competitive strength analysis data for radar chart.
    Returns metrics: Visibility, Sentiment, Position, Coverage, Growth
    """
    try:
        domain_id = request.GET.get('domain_id')
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
        your_prompts = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id,
            is_mention=True
        )
        
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
            comp_analytics = CompetitorPromptAnalytics.objects.filter(
                competitor=comp,
                is_mentioned=True
            )
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
            comp_analytics = CompetitorAnalytics.objects.filter(competitor=comp)
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
        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from domains.models import Domain
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)
        
        insights = []
        
        # Get competitors ordered by share of voice
        competitors = Competitor.objects.filter(domain_id=domain_id).order_by('-share_of_voice_percentage')
        
        if not competitors.exists():
            return Response(insights)
        
        # Get your brand's metrics
        your_prompts = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id,
            is_mention=True
        )
        your_mentions = your_prompts.count()
        your_sov = ShareOfVoiceAnalytics.objects.filter(
            domain_id=domain_id,
            competitor__isnull=True
        ).order_by('-timestamp').first()
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
            comp_analytics = CompetitorAnalytics.objects.filter(competitor=comp)
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
        comp_mentioned_prompts = CompetitorPromptAnalytics.objects.filter(
            competitor__domain_id=domain_id,
            is_mentioned=True,
            position__lte=5
        ).values_list('prompt_id', flat=True).distinct()
        
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
        
        return Response(insights[:4])  # Return top 4 insights
        
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
        
        if not domain_id:
            return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get your brand's mentioned prompts
        your_mentioned_prompts = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id,
            is_mention=True
        ).values_list('prompt_id', flat=True).distinct()
        
        # Get competitor mentioned prompts
        comp_filter = Q(competitor__domain_id=domain_id, is_mentioned=True, position__lte=10)
        if competitor_id:
            comp_filter &= Q(competitor_id=competitor_id)
        
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
            all_comp_mentions = CompetitorPromptAnalytics.objects.filter(
                prompt_id=prompt_id,
                competitor__domain_id=domain_id,
                is_mentioned=True
            )
            
            # Get your mentions for this prompt
            your_mentions_count = PromptAnalytics.objects.filter(
                prompt_id=prompt_id,
                prompt__group__domain_id=domain_id,
                is_mention=True
            ).count()
            
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

