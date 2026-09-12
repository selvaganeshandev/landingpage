from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Max
from domains.models import Domain
from .models import SentimentAnalytics, ShareOfVoiceAnalytics
from .serializers import SentimentAnalyticsSerializer, ShareOfVoiceAnalyticsSerializer
from core.queryset_scoping import filter_by_accessible_domains, user_can_access_domain

# Reserved platform label for the aggregate row written by the engine's
# competitor processor. Kept in sync with SOV_OVERALL_PLATFORM there.
SOV_OVERALL_PLATFORM = 'Overall'


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
    
    def _sentiment_window(self, domain_id, days):
        """The date window the page should read, and whether it had to fall back.

        The page asks for the last `days` days. Sentiment rows are only written
        when a domain is processed, so a domain that has not been swept recently
        has nothing in that window — and 28 of 74 production domains were showing
        0% across every card while months of real sentiment sat just outside it.

        When the requested window is empty, anchor the same-length window on the
        newest snapshot the domain has instead, and say so: the caller gets
        `as_of` (the snapshot date) and `stale=True`, and shows the figures with
        that date rather than a blank page. A domain with no rows at all still
        returns nothing.
        """
        today = timezone.now().date()
        start = today - timedelta(days=days)
        in_window = self.get_queryset().filter(
            domain_id=domain_id, snapshot_date__gte=start, snapshot_date__lte=today,
        ).exists()
        if in_window:
            return start, today, today, False
        latest = self.get_queryset().filter(domain_id=domain_id).aggregate(
            m=Max('snapshot_date'))['m']
        if latest is None:
            return start, today, None, False
        return latest - timedelta(days=days), latest, latest, True

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
        
        start_date, end_date, as_of, stale = self._sentiment_window(domain_id, days)
        queryset = self.get_queryset().filter(
            domain_id=domain_id,
            snapshot_date__gte=start_date,
            snapshot_date__lte=end_date,
        ).order_by('-snapshot_date', 'theme')
        
        serializer = self.get_serializer(queryset, many=True)
        # A list response cannot carry the window; the page reads `as_of` from
        # /summary/, which is always requested alongside this one.
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
        
        start_date, end_date, as_of, stale = self._sentiment_window(domain_id, days)
        
        # Current period: the NEWEST snapshot inside the window, not every row in
        # it. Each snapshot's mention_count is a cumulative total re-recorded on
        # every processing day, so summing across days counted the same mentions
        # once per snapshot — two days in the window read 660 for a true 330,
        # and a weekly sweep would have read ~4x. Same rule views_dashboard uses.
        in_window = self.get_queryset().filter(
            domain_id=domain_id,
            snapshot_date__gte=start_date,
            snapshot_date__lte=end_date
        )
        newest = in_window.aggregate(d=Max('snapshot_date'))['d']
        queryset = in_window.filter(snapshot_date=newest) if newest else in_window.none()
        if newest:
            as_of = newest
        
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
                'themes': [],
                'as_of': as_of,
                'stale': stale,
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
        
        # Previous period (same duration before current period) — likewise the
        # newest snapshot in THAT window, so the change compares one reading
        # against one reading rather than one against a pile.
        prev_start_date = start_date - timedelta(days=days)
        prev_window = self.get_queryset().filter(
            domain_id=domain_id,
            snapshot_date__gte=prev_start_date,
            snapshot_date__lt=start_date
        )
        prev_newest = prev_window.aggregate(d=Max('snapshot_date'))['d']
        prev_queryset = prev_window.filter(snapshot_date=prev_newest) if prev_newest else prev_window.none()
        
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
            'themes': list(themes),
            # Date the figures describe, and whether the requested window was
            # empty and the newest snapshot was used instead.
            'as_of': as_of,
            'stale': stale,
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
        
        # Share is stored once per platform plus an aggregate row per brand under
        # the reserved 'Overall' label. Without scoping, the latest timestamp
        # returns each brand once per platform — Tata Motors came back four times
        # over, so the chart legend listed "Tata 2179 mentions" beside "Tata 0
        # mentions" and every figure below was a different platform's row.
        #
        # Defaults to the aggregate; ?platform=ChatGPT asks for one platform.
        # scope=all returns every platform scope, which the page needs to build
        # its per-platform breakdown. The default stays aggregate-only: two
        # callers share this endpoint, and the one driving the headline figures
        # must not receive a brand once per platform.
        scope = request.query_params.get('scope')

        if platform:
            queryset = queryset.filter(platform=platform)
        elif scope == 'all':
            pass
        else:
            overall = queryset.filter(platform=SOV_OVERALL_PLATFORM)
            # Rows written before share was computed per platform carry the
            # literal 'ChatGPT' for what was an all-platform total, so a domain
            # that has not been recalculated still renders from them.
            queryset = overall if overall.exists() else queryset

        # Get latest data point for "You" and competitors
        latest_date = queryset.values_list('timestamp', flat=True).order_by('-timestamp').first()
        if latest_date:
            latest_queryset = queryset.filter(timestamp=latest_date)

            # One own-brand row per platform scope, not one overall.
            # `.filter(competitor__isnull=True).first()` returned a single row, so
            # under scope=all the brand appeared in whichever platform sorted
            # first and was absent from the others — Platform-Specific Share of
            # Voice listed Claude and Gemini with competitors only, as if the
            # brand had no presence there at all.
            result = []
            for row in latest_queryset.order_by('platform', 'market_position'):
                row_dict = ShareOfVoiceAnalyticsSerializer(row).data
                if row.competitor_id is None:
                    domain_name = row.domain.name if row.domain else 'You'
                    row_dict['brand_name'] = f'{domain_name} (You)'
                    row_dict['domain_name'] = domain_name
                    row_dict['is_you'] = True
                else:
                    row_dict['is_you'] = False
                result.append(row_dict)

            # Own brand first within each platform, then by market position, so a
            # consumer rendering a single scope still leads with "You".
            result.sort(key=lambda r: (
                r.get('platform') or '',
                not r.get('is_you'),
                r.get('market_position') or 999,
            ))

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

