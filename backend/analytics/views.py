from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg, Count
from domains.models import Domain
from .models import SentimentAnalytics, ShareOfVoiceAnalytics
from .serializers import SentimentAnalyticsSerializer, ShareOfVoiceAnalyticsSerializer
from core.queryset_scoping import filter_by_accessible_domains, user_can_access_domain


class SentimentAnalyticsViewSet(viewsets.ModelViewSet):
    serializer_class = SentimentAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Scoped to the user's accessible domains (org-wide for admins, granted
        # domains for users/clients) — tenant + domain isolation.
        return filter_by_accessible_domains(
            SentimentAnalytics.objects.all(), user, self.request
        )
    
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
            snapshot_date__gte=start_date
        ).order_by('-snapshot_date', 'theme')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get sentiment summary for a domain with previous period comparison."""
        domain_id = request.query_params.get('domain_id')
        days = int(request.query_params.get('days', 30))
        
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        
        # Current period
        queryset = self.get_queryset().filter(
            domain_id=domain_id,
            snapshot_date__gte=start_date,
            snapshot_date__lte=today
        )
        
        # Calculate weighted averages for current period
        total_mentions = queryset.aggregate(Sum('mention_count'))['mention_count__sum'] or 0
        
        if total_mentions == 0:
            return Response({
                'positive_percentage': 0,
                'neutral_percentage': 0,
                'negative_percentage': 0,
                'total_mentions': 0,
                'positive_change': 0,
                'neutral_change': 0,
                'negative_change': 0,
                'themes': []
            })
        
        # Calculate weighted percentages for current period
        weighted_positive = sum(
            (float(item.positive_percentage) * item.mention_count) for item in queryset
        ) / total_mentions
        weighted_neutral = sum(
            (float(item.neutral_percentage) * item.mention_count) for item in queryset
        ) / total_mentions
        weighted_negative = sum(
            (float(item.negative_percentage) * item.mention_count) for item in queryset
        ) / total_mentions
        
        # Previous period (same duration before current period)
        prev_start_date = start_date - timedelta(days=days)
        prev_queryset = self.get_queryset().filter(
            domain_id=domain_id,
            snapshot_date__gte=prev_start_date,
            snapshot_date__lt=start_date
        )
        
        # Calculate weighted averages for previous period
        prev_total_mentions = prev_queryset.aggregate(Sum('mention_count'))['mention_count__sum'] or 0
        
        if prev_total_mentions > 0:
            prev_weighted_positive = sum(
                (float(item.positive_percentage) * item.mention_count) for item in prev_queryset
            ) / prev_total_mentions
            prev_weighted_neutral = sum(
                (float(item.neutral_percentage) * item.mention_count) for item in prev_queryset
            ) / prev_total_mentions
            prev_weighted_negative = sum(
                (float(item.negative_percentage) * item.mention_count) for item in prev_queryset
            ) / prev_total_mentions
            
            # Calculate changes (percentage point difference)
            positive_change = round(weighted_positive - prev_weighted_positive, 2)
            neutral_change = round(weighted_neutral - prev_weighted_neutral, 2)
            negative_change = round(weighted_negative - prev_weighted_negative, 2)
        else:
            positive_change = 0
            neutral_change = 0
            negative_change = 0
        
        # Get top themes
        themes = queryset.values('theme').annotate(
            total_mentions=Sum('mention_count')
        ).order_by('-total_mentions')[:5]
        
        return Response({
            'positive_percentage': round(weighted_positive, 2),
            'neutral_percentage': round(weighted_neutral, 2),
            'negative_percentage': round(weighted_negative, 2),
            'total_mentions': total_mentions,
            'positive_change': positive_change,
            'neutral_change': neutral_change,
            'negative_change': negative_change,
            'themes': list(themes)
        })


    @action(detail=False, methods=['get'])
    def competitive(self, request):
        """Sentiment share for your brand and each competitor, computed identically.

        The Competitive Sentiment chart used to draw two different measures side
        by side: your bar came from SentimentAnalytics (daily theme percentages
        averaged by mention count) while competitor bars counted classified
        responses. Equal-length bars therefore did not mean equal evidence.

        Both sides are now the same statistic — the share of *responses that
        mentioned that brand* falling into each sentiment category, over one
        window. PromptAnalytics and CompetitorPromptAnalytics carry the same
        `sentiment_category` vocabulary (positive / neutral / negative), so the
        two populations are directly comparable.

        Query params:
            domain_id: Required
            days: Optional, default 30
        """
        domain_id = request.query_params.get('domain_id')
        try:
            days = int(request.query_params.get('days', 30))
        except (TypeError, ValueError):
            days = 30

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user_can_access_domain(request.user, domain_id, request):
            # 404 rather than 403 so the response cannot confirm a domain exists.
            return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)

        start = timezone.now() - timedelta(days=days)

        def _shares(counts, label, is_you):
            total = sum(counts.values())
            if not total:
                return None
            return {
                'name': label,
                'is_you': is_you,
                'responses': total,
                'positive': round(counts.get('positive', 0) * 100 / total, 1),
                'neutral': round(counts.get('neutral', 0) * 100 / total, 1),
                'negative': round(counts.get('negative', 0) * 100 / total, 1),
            }

        def _tally(queryset):
            tally = {}
            for row in queryset.values('sentiment_category').annotate(n=Count('id')):
                category = (row['sentiment_category'] or 'neutral').lower()
                if category not in ('positive', 'neutral', 'negative'):
                    category = 'neutral'
                tally[category] = tally.get(category, 0) + row['n']
            return tally

        results = []

        # Your brand: completed responses that actually named you. Responses with
        # no mention carry a default neutral category and would flatten the mix.
        from prompts.models import PromptAnalytics
        own = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id,
            track_status='COMP',
            is_mention=True,
            created_at__gte=start,
        )
        domain = Domain.objects.filter(id=domain_id).first()
        own_row = _shares(_tally(own), domain.name if domain else 'You', True)
        if own_row:
            results.append(own_row)

        # Competitors: the same statistic over responses that named them.
        from competitors.models import CompetitorPromptAnalytics
        competitor_rows = CompetitorPromptAnalytics.objects.filter(
            competitor__domain_id=domain_id,
            is_mentioned=True,
            created_at__gte=start,
        ).select_related('competitor')

        by_competitor = {}
        for row in competitor_rows.values('competitor__name', 'sentiment_category').annotate(n=Count('id')):
            name = row['competitor__name'] or 'Unknown'
            category = (row['sentiment_category'] or 'neutral').lower()
            if category not in ('positive', 'neutral', 'negative'):
                category = 'neutral'
            by_competitor.setdefault(name, {})
            by_competitor[name][category] = by_competitor[name].get(category, 0) + row['n']

        for name, counts in by_competitor.items():
            row = _shares(counts, name, False)
            if row:
                results.append(row)

        # You first, then most positive.
        results.sort(key=lambda r: (not r['is_you'], -r['positive'], r['name']))

        return Response({
            'days': days,
            'method': 'response_share',
            'results': results,
        })


class ShareOfVoiceAnalyticsViewSet(viewsets.ModelViewSet):
    serializer_class = ShareOfVoiceAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Scoped to the user's accessible domains (org-wide for admins, granted
        # domains for users/clients) — tenant + domain isolation.
        return filter_by_accessible_domains(
            ShareOfVoiceAnalytics.objects.all(), user, self.request
        )
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get share of voice for a specific domain, including 'You' (your domain) as first item."""
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
        
        # Get latest data point for "You" and competitors
        latest_date = queryset.values_list('timestamp', flat=True).order_by('-timestamp').first()
        if latest_date:
            latest_queryset = queryset.filter(timestamp=latest_date)
            your_data = latest_queryset.filter(competitor__isnull=True).first()
            competitors_data = latest_queryset.filter(competitor__isnull=False).order_by('market_position')
            
            # Build unified list with "You" first
            result = []
            if your_data:
                you_dict = ShareOfVoiceAnalyticsSerializer(your_data).data
                # Format as "Domain Name (You)" - get domain name from the data
                domain_name = your_data.domain.name if hasattr(your_data, 'domain') and your_data.domain else 'You'
                you_dict['brand_name'] = f'{domain_name} (You)'  # Format as "Brand Name (You)"
                you_dict['domain_name'] = domain_name  # Include domain_name for reference
                you_dict['is_you'] = True
                result.append(you_dict)
            
            for comp_data in competitors_data:
                comp_dict = ShareOfVoiceAnalyticsSerializer(comp_data).data
                comp_dict['is_you'] = False
                result.append(comp_dict)
            
            return Response(result)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def comparison(self, request):
        """Get market share comparison for a domain, including 'You' (your domain) as first item."""
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
        
        # Get your brand and competitors
        your_data = queryset.filter(competitor__isnull=True).first()
        competitors_data = queryset.filter(competitor__isnull=False).order_by('market_position')
        
        # Build unified list with "You" first
        all_brands = []
        if your_data:
            you_dict = ShareOfVoiceAnalyticsSerializer(your_data).data
            # Format as "Domain Name (You)" - get domain name from the data
            domain_name = your_data.domain.name if hasattr(your_data, 'domain') and your_data.domain else 'You'
            you_dict['brand_name'] = f'{domain_name} (You)'  # Format as "Brand Name (You)"
            you_dict['domain_name'] = domain_name  # Include domain_name for reference
            you_dict['is_you'] = True
            all_brands.append(you_dict)
        
        for comp_data in competitors_data:
            comp_dict = ShareOfVoiceAnalyticsSerializer(comp_data).data
            comp_dict['is_you'] = False
            all_brands.append(comp_dict)
        
        return Response({
            'brands': all_brands,  # Unified list with "You" first
            'total_market_mentions': queryset.aggregate(Sum('mention_count'))['mention_count__sum'] or 0
        })
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get latest Share of Voice analytics for a domain (matches engine endpoint).
        Returns data in the same format as engine /api/share-of-voice/
        """
        domain_id = request.query_params.get('domain_id')
        
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get latest timestamp
        latest = self.get_queryset().filter(
            domain_id=domain_id
        ).order_by('-timestamp').first()
        
        if not latest:
            return Response({
                'domain_id': int(domain_id),
                'message': 'No share of voice data available yet',
                'players': []
            })
        
        # Get all records for latest timestamp
        sov_data = self.get_queryset().filter(
            domain_id=domain_id,
            timestamp=latest.timestamp
        ).select_related('competitor', 'domain').order_by('market_position')
        
        serializer = self.get_serializer(sov_data, many=True)
        
        return Response({
            'domain_id': int(domain_id),
            'timestamp': latest.timestamp,
            'platform': latest.platform or 'Overall',
            'players': serializer.data
        })

