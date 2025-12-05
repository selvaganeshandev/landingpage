"""
Service layer for Agentic ChatBot
Provides reusable business logic for function calling tools
"""
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Count, Avg, Q, F
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ChatbotService:
    """Service class for chatbot function calling operations"""

    @staticmethod
    def _parse_date_range(date_range):
        """Convert date range string to datetime"""
        if date_range == 'all':
            return None
        days_map = {'7d': 7, '30d': 30, '90d': 90}
        days = days_map.get(date_range, 30)
        return timezone.now() - timedelta(days=days)

    @staticmethod
    def _serialize_value(value):
        """Convert non-JSON serializable types to JSON serializable types"""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, (date,)):
            return value.isoformat()
        return value

    @staticmethod
    def _serialize_dict(data):
        """Recursively serialize dictionary values"""
        if isinstance(data, dict):
            return {k: ChatbotService._serialize_value(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ChatbotService._serialize_dict(item) for item in data]
        return ChatbotService._serialize_value(data)

    @staticmethod
    def get_domain_analytics(domain, date_range='30d', include_trends=False):
        """Get comprehensive analytics for a domain"""
        from prompts.models import PromptAnalytics

        start_date = ChatbotService._parse_date_range(date_range)

        # Build query - filter by domain through prompt relationship
        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        )
        if start_date:
            mentions_query = mentions_query.filter(created_at__gte=start_date)

        # Basic metrics
        total_mentions = mentions_query.count()
        avg_position = mentions_query.aggregate(avg=Avg('position'))['avg'] or 0

        # Platform breakdown
        platform_breakdown = list(
            mentions_query.values('platform')
            .annotate(count=Count('id'), avg_pos=Avg('position'))
            .order_by('-count')
        )
        # Convert Decimal to float
        for item in platform_breakdown:
            if 'avg_pos' in item and item['avg_pos']:
                item['avg_pos'] = float(item['avg_pos'])

        # Sentiment breakdown using sentiment_category
        sentiment_breakdown = list(
            mentions_query.values('sentiment_category')
            .annotate(count=Count('id'))
        )

        result = {
            'total_mentions': total_mentions,
            'average_position': float(avg_position),
            'visibility_score': float(domain.visibility_score),
            'sentiment_score': float(domain.sentiment_score),
            'platform_breakdown': platform_breakdown,
            'sentiment_breakdown': sentiment_breakdown,
            'date_range': date_range
        }

        # Add trends if requested
        if include_trends:
            # Group by date for trend analysis
            from django.db.models.functions import TruncDate
            trends = list(
                mentions_query.annotate(date=TruncDate('created_at'))
                .values('date')
                .annotate(count=Count('id'), avg_pos=Avg('position'))
                .order_by('date')
            )
            # Convert Decimal to float in trends
            for item in trends:
                if 'avg_pos' in item and item['avg_pos']:
                    item['avg_pos'] = float(item['avg_pos'])
                if 'date' in item:
                    item['date'] = item['date'].isoformat()
            result['trends'] = trends

        return result

    @staticmethod
    def get_competitor_analysis(domain, competitor_names=None, metric='all'):
        """Analyze competitors and compare with domain"""
        from competitors.models import Competitor
        from prompts.models import PromptAnalytics

        # Get competitors for this domain
        competitors_query = Competitor.objects.filter(domain=domain)

        if competitor_names:
            competitors_query = competitors_query.filter(
                name__in=competitor_names
            )

        competitors = list(competitors_query)

        if not competitors:
            return {
                'message': 'No competitors tracked yet',
                'competitors': []
            }

        # Analyze each competitor using their stored metrics
        competitor_data = []
        for competitor in competitors:
            data = {
                'name': competitor.name,
                'url': competitor.url,
                'mention_count': competitor.total_mentions or 0,
                'avg_position': float(competitor.average_position or 0),
                'visibility_score': float(competitor.visibility_score or 0),
                'sentiment_score': float(competitor.sentiment_score or 0)
            }

            competitor_data.append(data)

        # Sort by mentions
        competitor_data.sort(key=lambda x: x['mention_count'], reverse=True)

        # Get domain's own metrics
        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        )

        domain_avg_result = domain_mentions.aggregate(avg=Avg('position'))['avg']

        return {
            'domain_name': domain.name,
            'domain_mentions': domain_mentions.count(),
            'domain_avg_position': float(domain_avg_result) if domain_avg_result else 0.0,
            'competitors': competitor_data,
            'total_competitors_tracked': len(competitors)
        }

    @staticmethod
    def get_prompt_performance(domain, platform='all', sort_by='mentions', limit=10):
        """Get performance metrics for tracked prompts"""
        from prompts.models import PromptGroup, PromptAnalytics

        # Get prompt groups with aggregated analytics
        prompt_groups = PromptGroup.objects.filter(domain=domain).annotate(
            mention_count=Count('prompts__analytics', filter=Q(prompts__analytics__is_mention=True)),
            avg_position=Avg('prompts__analytics__position', filter=Q(prompts__analytics__is_mention=True))
        ).filter(mention_count__gt=0)

        performance_data = []
        for group in prompt_groups:
            # Get analytics for filtering by platform
            analytics_query = PromptAnalytics.objects.filter(
                prompt__group=group,
                is_mention=True
            )

            if platform != 'all':
                analytics_query = analytics_query.filter(platform=platform)
                mention_count = analytics_query.count()
                avg_pos_result = analytics_query.aggregate(avg=Avg('position'))['avg']
                avg_pos = float(avg_pos_result) if avg_pos_result else 0.0
            else:
                mention_count = group.mention_count
                avg_pos = float(group.avg_position) if group.avg_position else 0.0

            if mention_count == 0:
                continue

            # Sentiment breakdown
            sentiment = analytics_query.values('sentiment_category').annotate(count=Count('id'))

            performance_data.append({
                'prompt_id': group.id,
                'prompt_text': group.theme or group.group_id,
                'mention_count': mention_count,
                'average_position': round(avg_pos, 2),
                'sentiment_breakdown': list(sentiment),
                'platforms': list(analytics_query.values('platform').annotate(count=Count('id')))
            })

        # Sort results
        sort_map = {
            'mentions': lambda x: x['mention_count'],
            'position': lambda x: x['average_position'],
            'recent': lambda x: x['prompt_id']  # Higher ID = more recent
        }

        if sort_by in sort_map:
            performance_data.sort(
                key=sort_map[sort_by],
                reverse=(sort_by != 'position')  # Position: lower is better
            )

        return {
            'prompts': performance_data[:limit],
            'total_prompts_tracked': PromptGroup.objects.filter(domain=domain).count(),
            'platform_filter': platform
        }

    @staticmethod
    def get_content_gaps(domain, limit=10, focus_area='all'):
        """Identify content gaps and opportunities"""
        from prompts.models import PromptGroup
        from competitors.models import Competitor

        gaps = []

        # 1. Prompts where domain has low visibility
        if focus_area in ['low_visibility', 'all']:
            low_vis_prompts = PromptGroup.objects.filter(domain=domain).annotate(
                mention_count=Count('prompts__analytics', filter=Q(prompts__analytics__is_mention=True)),
                avg_pos=Avg('prompts__analytics__position', filter=Q(prompts__analytics__is_mention=True))
            ).filter(
                Q(mention_count__lt=5) | Q(avg_pos__gt=5)
            )[:5]

            for prompt in low_vis_prompts:
                gaps.append({
                    'type': 'low_visibility',
                    'prompt': prompt.theme or prompt.group_id,
                    'issue': f'Only {prompt.mention_count} mentions or low position',
                    'suggestion': f'Create content targeting: "{prompt.theme or prompt.group_id}"'
                })

        # 2. Topics where competitors dominate
        if focus_area in ['competitor_strength', 'all']:
            competitors = Competitor.objects.filter(domain=domain)[:3]
            for competitor in competitors:
                if competitor.visibility_score and competitor.visibility_score > domain.visibility_score:
                    gaps.append({
                        'type': 'competitor_strength',
                        'competitor': competitor.name,
                        'issue': f'{competitor.name} has higher visibility score',
                        'suggestion': f'Analyze {competitor.name}\'s content strategy and create competitive content'
                    })

        # 3. Prompts with no mentions at all
        if focus_area in ['emerging_topics', 'all']:
            no_mention_prompts = PromptGroup.objects.filter(
                domain=domain
            ).annotate(
                mention_count=Count('prompts__analytics', filter=Q(prompts__analytics__is_mention=True))
            ).filter(mention_count=0)[:3]

            for prompt in no_mention_prompts:
                gaps.append({
                    'type': 'no_coverage',
                    'prompt': prompt.theme or prompt.group_id,
                    'issue': 'Zero mentions for this tracked prompt',
                    'suggestion': f'Create comprehensive content about: "{prompt.theme or prompt.group_id}"'
                })

        return {
            'gaps_identified': len(gaps),
            'gaps': gaps[:limit],
            'focus_area': focus_area
        }

    @staticmethod
    def get_sentiment_analysis(domain, date_range='30d', by_platform=False):
        """Get detailed sentiment analysis"""
        from prompts.models import PromptAnalytics

        start_date = ChatbotService._parse_date_range(date_range)

        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        )
        if start_date:
            mentions_query = mentions_query.filter(created_at__gte=start_date)

        # Overall sentiment breakdown
        sentiment_breakdown = list(
            mentions_query.values('sentiment_category')
            .annotate(count=Count('id'))
        )

        # Calculate percentages
        total = mentions_query.count()
        for item in sentiment_breakdown:
            item['percentage'] = round((item['count'] / total * 100), 2) if total > 0 else 0

        result = {
            'total_mentions': total,
            'sentiment_breakdown': sentiment_breakdown,
            'overall_sentiment_score': float(domain.sentiment_score),
            'date_range': date_range
        }

        # Platform breakdown if requested
        if by_platform:
            platform_sentiment = {}
            platforms = mentions_query.values_list('platform', flat=True).distinct()

            for platform in platforms:
                platform_mentions = mentions_query.filter(platform=platform)
                platform_sentiment[platform] = list(
                    platform_mentions.values('sentiment_category')
                    .annotate(count=Count('id'))
                )

            result['by_platform'] = platform_sentiment

        return result

    @staticmethod
    def get_top_mentions(domain, limit=5, sort_by='recent', platform='all'):
        """Get top mentions based on sorting criteria"""
        from prompts.models import PromptAnalytics

        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        ).select_related('prompt', 'prompt__group')

        if platform != 'all':
            mentions_query = mentions_query.filter(platform=platform)

        # Apply sorting
        sort_map = {
            'recent': '-created_at',
            'highest_position': 'position',  # Lower number = higher position
            'lowest_position': '-position',
            'sentiment': '-sentiment_score'
        }

        order_by = sort_map.get(sort_by, '-created_at')
        mentions = mentions_query.order_by(order_by)[:limit]

        return {
            'mentions': [
                {
                    'id': m.id,
                    'platform': m.platform,
                    'prompt': m.prompt.group.theme or m.prompt.prompt[:50] if m.prompt else 'Unknown',
                    'position': float(m.position),
                    'sentiment': m.sentiment_category,
                    'snippet': m.context_summary[:200] if m.context_summary else 'N/A',
                    'created_at': m.created_at.isoformat()
                }
                for m in mentions
            ],
            'sort_by': sort_by,
            'platform_filter': platform
        }

    @staticmethod
    def get_platform_breakdown(domain, metric='all', date_range='30d'):
        """Get platform-specific performance breakdown"""
        from prompts.models import PromptAnalytics

        start_date = ChatbotService._parse_date_range(date_range)

        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        )
        if start_date:
            mentions_query = mentions_query.filter(created_at__gte=start_date)

        platforms = mentions_query.values_list('platform', flat=True).distinct()

        platform_data = []
        for platform in platforms:
            platform_mentions = mentions_query.filter(platform=platform)

            avg_pos_result = platform_mentions.aggregate(avg=Avg('position'))['avg']
            data = {
                'platform': platform,
                'mention_count': platform_mentions.count(),
                'avg_position': float(avg_pos_result) if avg_pos_result else 0.0
            }

            if metric in ['sentiment', 'all']:
                sentiment = list(
                    platform_mentions.values('sentiment_category')
                    .annotate(count=Count('id'))
                )
                data['sentiment_breakdown'] = sentiment

            platform_data.append(data)

        # Sort by mention count
        platform_data.sort(key=lambda x: x['mention_count'], reverse=True)

        return {
            'platforms': platform_data,
            'date_range': date_range,
            'metric': metric
        }

    @staticmethod
    def get_insights_dashboard(domain, date_range='30d'):
        """Get comprehensive insights dashboard data"""
        from prompts.models import PromptAnalytics
        from alerts.models import Alert

        start_date = ChatbotService._parse_date_range(date_range)

        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        )
        if start_date:
            mentions_query = mentions_query.filter(created_at__gte=start_date)

        # Key metrics
        total_mentions = mentions_query.count()
        avg_position = mentions_query.aggregate(avg=Avg('position'))['avg'] or 0

        # Active alerts
        active_alerts = Alert.objects.filter(domain=domain, status='active').count()

        # Platform distribution
        platform_breakdown = list(
            mentions_query.values('platform')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Sentiment distribution
        sentiment_breakdown = list(
            mentions_query.values('sentiment_category')
            .annotate(count=Count('id'))
        )

        # Recent trend (last 7 days)
        from django.db.models.functions import TruncDate
        last_7_days = timezone.now() - timedelta(days=7)
        trend_data = list(
            mentions_query.filter(created_at__gte=last_7_days)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        # Convert dates to ISO format for JSON serialization
        for item in trend_data:
            if 'date' in item:
                item['date'] = item['date'].isoformat()

        return {
            'total_mentions': total_mentions,
            'average_position': float(avg_position),
            'visibility_score': float(domain.visibility_score),
            'sentiment_score': float(domain.sentiment_score),
            'active_alerts': active_alerts,
            'platform_breakdown': platform_breakdown,
            'sentiment_breakdown': sentiment_breakdown,
            'trend_data': trend_data,
            'date_range': date_range
        }

    @staticmethod
    def get_mentions_list(domain, platform='all', sentiment='all', search_query=None, limit=10, sort_by='recent'):
        """Get detailed list of mentions with filters"""
        from prompts.models import PromptAnalytics

        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        ).select_related('prompt', 'prompt__group')

        # Apply filters
        if platform != 'all':
            mentions_query = mentions_query.filter(platform=platform)

        if sentiment != 'all':
            mentions_query = mentions_query.filter(sentiment_category=sentiment)

        if search_query:
            mentions_query = mentions_query.filter(
                Q(context_summary__icontains=search_query) |
                Q(prompt__prompt__icontains=search_query)
            )

        # Apply sorting
        sort_map = {
            'recent': '-created_at',
            'position': 'position',
            'sentiment': '-sentiment_score'
        }
        order_by = sort_map.get(sort_by, '-created_at')

        total_count = mentions_query.count()
        mentions = mentions_query.order_by(order_by)[:limit]

        return {
            'mentions': [
                {
                    'id': m.id,
                    'platform': m.platform,
                    'prompt': m.prompt.group.theme or m.prompt.prompt[:50] if m.prompt else 'N/A',
                    'position': float(m.position),
                    'sentiment': m.sentiment_category,
                    'sentiment_score': float(m.sentiment_score),
                    'snippet': m.context_summary[:200] if m.context_summary else 'N/A',
                    'created_at': m.created_at.isoformat()
                }
                for m in mentions
            ],
            'total_count': total_count,
            'filters_applied': {
                'platform': platform,
                'sentiment': sentiment,
                'search_query': search_query
            },
            'sort_by': sort_by
        }

    @staticmethod
    def get_citations_list(domain, platform='all', status='all', limit=10):
        """Get citations where domain was mentioned"""
        from misinformation.models import CitationURL

        citations_query = CitationURL.objects.filter(domain=domain)

        # Apply filters
        if platform != 'all':
            # Platform info would be in the prompt_analytics
            citations_query = citations_query.filter(prompt_analytics__platform=platform)

        if status != 'all':
            # Map status to crawl_status
            status_map = {
                'verified': 'success',
                'pending': 'pending',
                'flagged': 'failed'
            }
            crawl_status = status_map.get(status, status)
            citations_query = citations_query.filter(crawl_status=crawl_status)

        total_count = citations_query.count()
        citations = citations_query.select_related('prompt_analytics').order_by('-created_at')[:limit]

        return {
            'citations': [
                {
                    'id': c.id,
                    'url': c.url[:100] + '...' if len(c.url) > 100 else c.url,
                    'platform': c.prompt_analytics.platform if hasattr(c, 'prompt_analytics') and c.prompt_analytics else 'N/A',
                    'crawl_status': c.crawl_status,
                    'http_status': c.http_status_code,
                    'last_crawled': c.last_crawled_at.isoformat() if c.last_crawled_at else None,
                    'created_at': c.created_at.isoformat()
                }
                for c in citations
            ],
            'total_count': total_count,
            'filters_applied': {
                'platform': platform,
                'status': status
            }
        }

    @staticmethod
    def get_alerts_list(domain, status='all', severity='all', limit=10):
        """Get active alerts and alert rules"""
        from alerts.models import Alert, AlertRule

        # Get alerts
        alerts_query = Alert.objects.filter(domain=domain)

        if status != 'all':
            alerts_query = alerts_query.filter(status=status)

        if severity != 'all':
            alerts_query = alerts_query.filter(severity=severity)

        alerts_count = alerts_query.count()
        alerts = alerts_query[:limit]

        # Get alert rules
        rules = AlertRule.objects.filter(domain=domain, enabled=True)

        return {
            'alerts': [
                {
                    'id': a.id,
                    'type': a.type,
                    'severity': a.severity,
                    'title': a.title,
                    'message': a.message,
                    'status': a.status,
                    'platform': a.platform,
                    'created_at': a.created_at.isoformat()
                }
                for a in alerts
            ],
            'alert_rules': [
                {
                    'id': r.id,
                    'name': r.name,
                    'description': r.description,
                    'enabled': r.enabled,
                    'detection_count': r.detection_count,
                    'last_triggered_at': r.last_triggered_at.isoformat() if r.last_triggered_at else None
                }
                for r in rules
            ],
            'total_alerts': alerts_count,
            'total_rules': rules.count(),
            'filters_applied': {
                'status': status,
                'severity': severity
            }
        }

    @staticmethod
    def get_topics_analysis(domain, date_range='30d', limit=10):
        """Analyze topics and themes in mentions"""
        from prompts.models import PromptAnalytics

        start_date = ChatbotService._parse_date_range(date_range)

        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True
        )
        if start_date:
            mentions_query = mentions_query.filter(created_at__gte=start_date)

        # Group by prompt group theme (topics)
        topics = list(
            mentions_query.values('prompt__group__theme', 'prompt__group__group_id')
            .annotate(
                mention_count=Count('id'),
                avg_position=Avg('position'),
                avg_sentiment=Avg('sentiment_score')
            )
            .order_by('-mention_count')
            [:limit]
        )

        # Format response
        topics_formatted = [
            {
                'topic': t['prompt__group__theme'] or t['prompt__group__group_id'] or 'Uncategorized',
                'mention_count': t['mention_count'],
                'average_position': float(t['avg_position']) if t['avg_position'] else 0.0,
                'average_sentiment': float(t['avg_sentiment']) if t['avg_sentiment'] else 0.0
            }
            for t in topics
        ]

        return {
            'topics': topics_formatted,
            'total_topics': len(topics),
            'date_range': date_range
        }

    @staticmethod
    def get_share_of_voice(domain, date_range='30d', include_competitors=False):
        """Get share of voice analysis"""
        from analytics.models import ShareOfVoiceAnalytics
        from competitors.models import Competitor

        start_date = ChatbotService._parse_date_range(date_range)

        # Get domain's share of voice
        sov_query = ShareOfVoiceAnalytics.objects.filter(domain=domain)
        if start_date:
            sov_query = sov_query.filter(timestamp__gte=start_date)

        # Domain's own SOV (where competitor is NULL)
        domain_sov = sov_query.filter(competitor__isnull=True).order_by('-timestamp').first()

        result = {
            'domain_name': domain.name,
            'share_percentage': float(domain_sov.share_percentage) if domain_sov else 0.0,
            'mention_count': domain_sov.mention_count if domain_sov else 0,
            'market_position': domain_sov.market_position if domain_sov else None,
            'date_range': date_range
        }

        # Include competitor breakdown if requested
        if include_competitors:
            competitor_sov = list(
                sov_query.filter(competitor__isnull=False)
                .order_by('-timestamp', 'market_position')
                .values('competitor__name', 'share_percentage', 'mention_count', 'market_position')
                [:10]
            )

            result['competitors'] = [
                {
                    'name': c['competitor__name'],
                    'share_percentage': float(c['share_percentage']),
                    'mention_count': c['mention_count'],
                    'market_position': c['market_position']
                }
                for c in competitor_sov
            ]

        return result

    @staticmethod
    def get_historical_trends(domain, metric='all', period='daily', months=3):
        """Get historical trends showing metrics over time"""
        from prompts.models import PromptAnalytics
        from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

        # Calculate date range
        start_date = timezone.now() - timedelta(days=months * 30)

        mentions_query = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True,
            created_at__gte=start_date
        )

        # Choose truncation function based on period
        trunc_func_map = {
            'daily': TruncDate,
            'weekly': TruncWeek,
            'monthly': TruncMonth
        }
        trunc_func = trunc_func_map.get(period, TruncDate)

        # Build aggregation
        trends = list(
            mentions_query
            .annotate(date=trunc_func('created_at'))
            .values('date')
            .annotate(
                mentions=Count('id'),
                avg_position=Avg('position'),
                avg_sentiment=Avg('sentiment_score')
            )
            .order_by('date')
        )

        # Format response based on metric filter
        formatted_trends = []
        for t in trends:
            trend_data = {'date': t['date'].isoformat()}

            if metric in ['mentions', 'all']:
                trend_data['mentions'] = t['mentions']
            if metric in ['position', 'all']:
                avg_pos = float(t['avg_position']) if t['avg_position'] else 0.0
                trend_data['average_position'] = round(avg_pos, 2)
            if metric in ['sentiment', 'all']:
                avg_sent = float(t['avg_sentiment']) if t['avg_sentiment'] else 0.0
                trend_data['average_sentiment'] = round(avg_sent, 2)
            if metric in ['visibility', 'all']:
                # Calculate simple visibility score
                avg_pos_val = float(t['avg_position']) if t['avg_position'] else 10.0
                visibility = (1 / avg_pos_val) * 100 if avg_pos_val else 0
                trend_data['visibility_score'] = round(visibility, 2)

            formatted_trends.append(trend_data)

        return {
            'trends': formatted_trends,
            'metric': metric,
            'period': period,
            'months': months,
            'data_points': len(formatted_trends)
        }

    @staticmethod
    def get_prompt_groups(domain, limit=10, sort_by='mentions'):
        """Get prompt groups (collections of related prompts)"""
        from prompts.models import PromptGroup

        # Get prompt groups with aggregated data from analytics
        prompt_groups = PromptGroup.objects.filter(domain=domain).annotate(
            mention_count=Count('prompts__analytics', filter=Q(prompts__analytics__is_mention=True)),
            avg_position=Avg('prompts__analytics__position', filter=Q(prompts__analytics__is_mention=True))
        )

        # Apply sorting
        sort_map = {
            'mentions': '-mention_count',
            'recent': '-modified_at',
            'performance': 'avg_position'  # Lower position is better
        }
        order_by = sort_map.get(sort_by, '-mention_count')
        prompt_groups = prompt_groups.order_by(order_by)[:limit]

        return {
            'prompt_groups': [
                {
                    'id': pg.id,
                    'name': pg.theme or pg.group_id,
                    'mention_count': pg.mention_count,
                    'average_position': float(pg.avg_position) if pg.avg_position else 0.0,
                    'variants_count': pg.prompts.count()
                }
                for pg in prompt_groups
            ],
            'total_groups': PromptGroup.objects.filter(domain=domain).count(),
            'sort_by': sort_by
        }

    @staticmethod
    def get_misinformation_alerts(domain, status='all', limit=10):
        """Get misinformation and accuracy alerts"""
        from alerts.models import Alert

        # Filter for misinformation alerts
        alerts_query = Alert.objects.filter(
            domain=domain,
            type='misinformation'
        )

        if status != 'all':
            alerts_query = alerts_query.filter(status=status)

        total_count = alerts_query.count()
        alerts = alerts_query.order_by('-created_at')[:limit]

        # Count by severity
        severity_breakdown = list(
            alerts_query.values('severity')
            .annotate(count=Count('id'))
        )

        return {
            'alerts': [
                {
                    'id': a.id,
                    'title': a.title,
                    'message': a.message,
                    'severity': a.severity,
                    'status': a.status,
                    'platform': a.platform,
                    'created_at': a.created_at.isoformat(),
                    'resolved_at': a.resolved_at.isoformat() if a.resolved_at else None
                }
                for a in alerts
            ],
            'total_count': total_count,
            'severity_breakdown': severity_breakdown,
            'status_filter': status
        }

    @staticmethod
    def get_domain_summary(domain):
        """Get comprehensive summary of domain"""
        from prompts.models import PromptAnalytics, PromptGroup
        from competitors.models import Competitor
        from alerts.models import Alert

        # Last 30 days data
        last_30_days = timezone.now() - timedelta(days=30)

        mentions_30d = PromptAnalytics.objects.filter(
            prompt__group__domain=domain,
            is_mention=True,
            created_at__gte=last_30_days
        )

        # Core metrics
        total_mentions = mentions_30d.count()
        avg_position_result = mentions_30d.aggregate(avg=Avg('position'))['avg']
        avg_position = float(avg_position_result) if avg_position_result else 0.0

        # Platform breakdown
        platforms = list(
            mentions_30d.values('platform')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Sentiment summary
        sentiment = list(
            mentions_30d.values('sentiment_category')
            .annotate(count=Count('id'))
        )

        # Active alerts
        active_alerts = Alert.objects.filter(domain=domain, status='active').count()

        # Tracked items
        tracked_prompts = PromptGroup.objects.filter(domain=domain).count()
        tracked_competitors = Competitor.objects.filter(domain=domain).count()

        return {
            'domain_name': domain.name,
            'domain_url': domain.url,
            'summary_period': '30 days',
            'metrics': {
                'total_mentions': total_mentions,
                'average_position': round(avg_position, 2),
                'visibility_score': float(domain.visibility_score),
                'sentiment_score': float(domain.sentiment_score)
            },
            'platform_breakdown': platforms,
            'sentiment_breakdown': sentiment,
            'tracking': {
                'prompt_groups': tracked_prompts,
                'competitors': tracked_competitors
            },
            'alerts': {
                'active_count': active_alerts
            },
            'generated_at': timezone.now().isoformat()
        }
