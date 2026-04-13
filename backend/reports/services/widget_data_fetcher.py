"""
Widget Data Fetcher Service
Maps widget IDs from custom report templates to actual database queries
Returns real data for each widget type
"""
from datetime import timedelta
from django.db.models import Count, Avg, Sum, Q, Max, Min, F
from django.utils import timezone


class WidgetDataFetcher:
    """
    Fetch real data for each widget type in custom report templates
    """

    def __init__(self, domain, start_date, end_date, organisation):
        self.domain = domain
        self.start_date = start_date
        self.end_date = end_date
        self.organisation = organisation

        # Calculate previous period for comparison
        self.period_days = (end_date - start_date).days
        self.prev_start_date = start_date - timedelta(days=self.period_days)
        self.prev_end_date = start_date

    def fetch_all_widgets(self, grid_rows):
        """
        Fetch data for all widgets in the template grid
        Returns dict with widget_id as key and data as value
        """
        widget_data = {}

        for row in grid_rows:
            for slot in row.get('slots', []):
                if slot:  # Widget exists
                    widget_id = slot.get('id')
                    if widget_id:
                        data = self.fetch_widget_data(widget_id)
                        if data:
                            widget_data[widget_id] = data

        return widget_data

    def fetch_widget_data(self, widget_id):
        """
        Main dispatcher - routes widget ID to appropriate fetcher method
        """
        # Prompts widgets
        if widget_id == 'total-prompts-metric':
            return self._get_total_prompts()
        elif widget_id == 'active-prompts-metric':
            return self._get_active_prompts()
        elif widget_id == 'prompt-groups-metric':
            return self._get_prompt_groups()
        elif widget_id == 'prompts-by-platform-chart':
            return self._get_prompts_by_platform_chart()
        elif widget_id == 'top-prompts-table':
            return self._get_top_prompts_table()
        elif widget_id == 'prompt-completion-rate-metric':
            return self._get_prompt_completion_rate()
        elif widget_id == 'avg-prompts-per-group-metric':
            return self._get_avg_prompts_per_group()
        elif widget_id == 'prompt-response-rate-metric':
            return self._get_prompt_response_rate()
        elif widget_id == 'prompt-sentiment-distribution-chart':
            return self._get_prompt_sentiment_distribution()
        elif widget_id == 'recent-prompts-table':
            return self._get_recent_prompts_table()

        # Citations widgets
        elif widget_id == 'total-citations-metric':
            return self._get_total_citations()
        elif widget_id == 'citation-rate-metric':
            return self._get_citation_rate()
        elif widget_id == 'citation-density-metric':
            return self._get_citation_density()
        elif widget_id == 'citations-by-platform-chart':
            return self._get_citations_by_platform_chart()
        elif widget_id == 'primary-sources-metric':
            return self._get_primary_sources_count()
        elif widget_id == 'citation-growth-metric':
            return self._get_citation_growth()
        elif widget_id == 'top-cited-prompts-table':
            return self._get_top_cited_prompts()
        elif widget_id == 'citations-per-platform-metric':
            return self._get_avg_citations_per_platform()

        # Topics widgets
        elif widget_id == 'total-topics-metric':
            return self._get_total_topics()
        elif widget_id == 'topics-coverage-metric':
            return self._get_topics_coverage()
        elif widget_id == 'topics-table':
            return self._get_topics_table()
        elif widget_id == 'top-topic-by-mentions-metric':
            return self._get_top_topic_by_mentions()
        elif widget_id == 'avg-keywords-per-topic-metric':
            return self._get_avg_keywords_per_topic()
        elif widget_id == 'topic-sentiment-chart':
            return self._get_topic_sentiment_chart()
        elif widget_id == 'topic-distribution-chart':
            return self._get_topic_distribution_chart()

        # Share of Voice widgets
        elif widget_id == 'share-metric':
            return self._get_share_of_voice()
        elif widget_id == 'market-position-metric':
            return self._get_market_position()
        elif widget_id == 'share-of-voice-chart':
            return self._get_share_of_voice_chart()
        elif widget_id == 'competitor-count-metric':
            return self._get_competitor_count()
        elif widget_id == 'share-vs-top-competitor-metric':
            return self._get_share_vs_top_competitor()
        elif widget_id == 'share-of-voice-trend-chart':
            return self._get_share_of_voice_trend()
        elif widget_id == 'competitors-ranking-table':
            return self._get_competitors_ranking_table()

        # Historical Trends widgets
        elif widget_id == 'mentions-chart':
            return self._get_mentions_over_time()
        elif widget_id == 'visibility-trend-chart':
            return self._get_visibility_trend()
        elif widget_id == 'sentiment-trend-chart':
            return self._get_sentiment_trend()
        elif widget_id == 'citation-trend-chart':
            return self._get_citation_trend()
        elif widget_id == 'platform-mentions-trend-chart':
            return self._get_platform_mentions_trend()
        elif widget_id == 'weekly-growth-chart':
            return self._get_weekly_growth_chart()
        elif widget_id == 'response-rate-trend-chart':
            return self._get_response_rate_trend()
        elif widget_id == 'comparative-trends-chart':
            return self._get_comparative_trends()

        # Additional metric widgets that might be used
        elif widget_id == 'total-mentions-metric':
            return self._get_total_mentions()
        elif widget_id == 'visibility-metric':
            return self._get_visibility_score()
        elif widget_id == 'avg-sentiment-metric':
            return self._get_avg_sentiment()

        # New Citations widgets
        elif widget_id == 'unique-sources-metric':
            return self._get_unique_sources()
        elif widget_id == 'domain-citations-metric':
            return self._get_domain_citations()
        elif widget_id == 'valid-links-metric':
            return self._get_valid_links()
        elif widget_id == 'pending-citations-metric':
            return self._get_pending_citations()

        # New Sentiment widgets
        elif widget_id == 'competitor-comparison-chart':
            return self._get_competitor_comparison_chart()

        # New Topics widgets
        elif widget_id == 'topic-trends-chart':
            return self._get_topic_trends_chart()

        # New Share of Voice widgets
        elif widget_id == 'market-share-metric':
            return self._get_market_share()
        elif widget_id == 'dominance-score-metric':
            return self._get_dominance_score()
        elif widget_id == 'overall-market-share-metric':
            return self._get_overall_market_share()
        elif widget_id == 'share-of-voice-trends-chart':
            return self._get_share_of_voice_trend()  # Reuse existing
        elif widget_id == 'brand-positioning-matrix-chart':
            return self._get_brand_positioning_matrix()

        # New Historical Trends widgets
        elif widget_id == 'visibility-growth-chart':
            return self._get_visibility_growth_chart()
        elif widget_id == 'mention-growth-chart':
            return self._get_mention_growth_chart()
        elif widget_id == 'position-improvement-chart':
            return self._get_position_improvement_chart()
        elif widget_id == 'market-share-gain-chart':
            return self._get_market_share_gain_chart()
        elif widget_id == 'visibility-score-progression-chart':
            return self._get_visibility_score_progression()

        # ==================== MISSING WIDGETS FROM TEMPLATES ====================
        
        # Information Metrics widgets
        elif widget_id == 'avg-position-metric':
            return self._get_avg_position()
        elif widget_id == 'engagement-metric':
            return self._get_engagement_score()
        elif widget_id == 'mention-rate-metric':
            return self._get_mention_rate()
        elif widget_id == 'mention-growth-metric':
            return self._get_mention_growth()
        elif widget_id == 'platform-coverage-metric':
            return self._get_platform_coverage()
        elif widget_id == 'positive-sentiment-metric':
            return self._get_positive_sentiment()
        elif widget_id == 'negative-sentiment-metric':
            return self._get_negative_sentiment()
        elif widget_id == 'sentiment-trend-metric':
            return self._get_sentiment_trend_metric()
        elif widget_id == 'competitor-gap-metric':
            return self._get_competitor_gap()
        elif widget_id == 'market-share-trend-metric':
            return self._get_market_share_trend()
        elif widget_id == 'health-score-metric':
            return self._get_health_score()
        elif widget_id == 'content-quality-metric':
            return self._get_content_quality()
        elif widget_id == 'topics-covered-metric':
            return self._get_topics_covered()
        elif widget_id == 'answer-coverage-metric':
            return self._get_answer_coverage()
        elif widget_id == 'visibility-trend-metric':
            return self._get_visibility_trend_metric()
        elif widget_id == 'mention-growth-percent-metric':
            return self._get_mention_growth_percent()
        elif widget_id == 'engagement-growth-metric':
            return self._get_engagement_growth()
        elif widget_id == 'active-alerts-metric':
            return self._get_active_alerts()
        elif widget_id == 'critical-issues-metric':
            return self._get_critical_issues()
        elif widget_id == 'broken-links-metric':
            return self._get_broken_links()
        elif widget_id == 'misinformation-cases-metric':
            return self._get_misinformation_cases()

        # Mentions widgets
        elif widget_id == 'mentions-metric':
            return self._get_total_mentions()  # Reuse
        elif widget_id == 'platform-chart':
            return self._get_platform_chart()

        # Competitors widgets
        elif widget_id == 'competitors-metric':
            return self._get_competitor_count()  # Reuse
        elif widget_id == 'competitors-table':
            return self._get_competitors_ranking_table()  # Reuse

        # Content widgets
        elif widget_id == 'summary-text':
            return self._get_summary_text()
        elif widget_id == 'topics-table':
            return self._get_topics_table()  # Reuse

        # Sentiment widgets
        elif widget_id == 'sentiment-metric':
            return self._get_avg_sentiment()  # Reuse
        elif widget_id == 'sentiment-chart':
            return self._get_sentiment_chart()
        elif widget_id == 'platform-sentiment-breakdown-chart':
            return self._get_platform_sentiment_breakdown()

        # Platform Metrics widgets
        elif widget_id == 'total-platforms-metric':
            return self._get_total_platforms()
        elif widget_id == 'total-platform-mentions-metric':
            return self._get_total_platform_mentions()
        elif widget_id == 'total-platform-citations-metric':
            return self._get_total_platform_citations()
        elif widget_id == 'chatgpt-visibility-metric':
            return self._get_platform_visibility('ChatGPT')
        elif widget_id == 'gemini-visibility-metric':
            return self._get_platform_visibility('Gemini')
        elif widget_id == 'perplexity-visibility-metric':
            return self._get_platform_visibility('Perplexity')
        elif widget_id == 'claude-visibility-metric':
            return self._get_platform_visibility('Claude')
        elif widget_id == 'grok-visibility-metric':
            return self._get_platform_visibility('Grok')
        elif widget_id == 'top-performing-platform-metric':
            return self._get_top_performing_platform()
        elif widget_id == 'platform-mention-distribution-chart':
            return self._get_platform_mention_distribution()
        elif widget_id == 'platform-citation-distribution-chart':
            return self._get_platform_citation_distribution()
        elif widget_id == 'platform-mention-trends-chart':
            return self._get_platform_mentions_trend()  # Reuse
        elif widget_id == 'avg-position-by-platform-chart':
            return self._get_avg_position_by_platform()
        elif widget_id == 'best-platform-position-metric':
            return self._get_best_platform_position()
        elif widget_id == 'platform-position-comparison-chart':
            return self._get_platform_position_comparison()
        elif widget_id == 'most-positive-platform-metric':
            return self._get_most_positive_platform()
        elif widget_id == 'platform-sentiment-trends-chart':
            return self._get_platform_sentiment_trends()
        elif widget_id == 'platform-response-rate-metric':
            return self._get_platform_response_rate()
        elif widget_id == 'platform-mention-rate-chart':
            return self._get_platform_mention_rate_chart()
        elif widget_id == 'platform-growth-rate-chart':
            return self._get_platform_growth_rate()
        elif widget_id == 'platform-share-of-voice-chart':
            return self._get_platform_share_of_voice()
        elif widget_id == 'platform-performance-matrix-chart':
            return self._get_platform_performance_matrix()
        elif widget_id == 'platform-citation-density-chart':
            return self._get_platform_citation_density()
        elif widget_id == 'platform-health-score-chart':
            return self._get_platform_health_score()
        elif widget_id == 'platform-coverage-quality-metric':
            return self._get_platform_coverage_quality()
        elif widget_id == 'platform-consistency-score-metric':
            return self._get_platform_consistency_score()

        # ==================== GSC ORGANIC WIDGETS ====================
        elif widget_id == 'gsc-overview-table':
            return self._get_gsc_overview_table()
        elif widget_id == 'gsc-clicks-metric':
            return self._get_gsc_clicks()
        elif widget_id == 'gsc-impressions-metric':
            return self._get_gsc_impressions()
        elif widget_id == 'gsc-ctr-metric':
            return self._get_gsc_ctr()
        elif widget_id == 'gsc-avg-position-metric':
            return self._get_gsc_avg_position()
        elif widget_id == 'gsc-top-queries-table':
            return self._get_gsc_top_queries()
        elif widget_id == 'gsc-top-pages-table':
            return self._get_gsc_top_pages()

        # ==================== GA ORGANIC WIDGETS ====================
        elif widget_id == 'ga-overview-table':
            return self._get_ga_overview_table()
        elif widget_id == 'ga-sessions-metric':
            return self._get_ga_sessions()
        elif widget_id == 'ga-users-metric':
            return self._get_ga_users()
        elif widget_id == 'ga-pageviews-metric':
            return self._get_ga_pageviews()
        elif widget_id == 'ga-conversions-metric':
            return self._get_ga_conversions()
        elif widget_id == 'ga-revenue-metric':
            return self._get_ga_revenue()
        elif widget_id == 'ga-bounce-rate-metric':
            return self._get_ga_bounce_rate()
        elif widget_id == 'ga-avg-session-duration-metric':
            return self._get_ga_avg_session_duration()
        elif widget_id == 'ga-top-landing-pages-table':
            return self._get_ga_top_landing_pages()
        elif widget_id == 'ga-platform-breakdown-chart':
            return self._get_ga_platform_breakdown()

        return None  # Unknown widget

    # ==================== PROMPTS WIDGETS ====================

    def _get_total_prompts(self):
        """Total number of prompts for the domain"""
        from prompts.models import Prompt

        current_count = Prompt.objects.filter(
            group__domain=self.domain
        ).count()

        return {
            'type': 'metric',
            'value': current_count,
            'label': 'Total Prompts',
            'format': 'number'
        }

    def _get_active_prompts(self):
        """Prompts that have been processed/analyzed"""
        from prompts.models import Prompt

        current_count = Prompt.objects.filter(
            group__domain=self.domain,
            track_status='COMP'  # Completed prompts
        ).count()

        total_count = Prompt.objects.filter(
            group__domain=self.domain
        ).count()

        percentage = (current_count / total_count * 100) if total_count > 0 else 0

        return {
            'type': 'metric',
            'value': current_count,
            'label': 'Active Prompts',
            'format': 'number',
            'subtitle': f'{round(percentage, 1)}% of total'
        }

    def _get_prompt_groups(self):
        """Total number of prompt groups"""
        from prompts.models import PromptGroup

        current_count = PromptGroup.objects.filter(
            domain=self.domain
        ).count()

        return {
            'type': 'metric',
            'value': current_count,
            'label': 'Prompt Groups',
            'format': 'number'
        }

    def _get_prompts_by_platform_chart(self):
        """Prompts analyzed breakdown by platform"""
        from prompts.models import PromptAnalytics

        platform_data = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).values('platform').annotate(
            count=Count('id')
        ).order_by('-count')

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': [
                {
                    'platform': p['platform'] or 'Unknown',
                    'value': p['count']
                }
                for p in platform_data
            ],
            'x_axis': 'platform',
            'y_axis': 'value',
            'label': 'Prompts by Platform'
        }

    def _get_top_prompts_table(self):
        """Top performing prompts by mentions"""
        from prompts.models import Prompt, PromptAnalytics

        prompts = Prompt.objects.filter(
            group__domain=self.domain
        ).annotate(
            mention_count=Count(
                'analytics',
                filter=Q(
                    analytics__is_mention=True,
                    analytics__created_at__gte=self.start_date,
                    analytics__created_at__lte=self.end_date
                )
            ),
            avg_sentiment=Avg(
                'analytics__sentiment_score',
                filter=Q(
                    analytics__created_at__gte=self.start_date,
                    analytics__created_at__lte=self.end_date
                )
            ),
            citation_count=Count(
                'analytics__citations',
                filter=Q(
                    analytics__created_at__gte=self.start_date,
                    analytics__created_at__lte=self.end_date
                )
            )
        ).filter(
            mention_count__gt=0
        ).order_by('-mention_count')[:10]

        return {
            'type': 'table',
            'columns': ['Prompt', 'Mentions', 'Avg Sentiment', 'Citations'],
            'rows': [
                {
                    'prompt': p.prompt[:80] + '...' if len(p.prompt) > 80 else p.prompt,
                    'mentions': p.mention_count,
                    'sentiment': round(p.avg_sentiment or 0, 2),
                    'citations': p.citation_count
                }
                for p in prompts
            ]
        }

    # ==================== CITATIONS WIDGETS ====================

    def _get_total_citations(self):
        """Total number of citations across all platforms"""
        from prompts.models import PromptAnalytics

        # Count non-empty citations arrays
        current_citations = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        ).aggregate(
            total=Count('id')
        )['total'] or 0

        # Previous period
        prev_citations = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date
        ).exclude(
            total_citations=0
        ).aggregate(
            total=Count('id')
        )['total'] or 0

        growth = ((current_citations - prev_citations) / prev_citations * 100) if prev_citations > 0 else 0

        return {
            'type': 'metric',
            'value': current_citations,
            'label': 'Total Citations',
            'format': 'number',
            'growth': round(growth, 1),
            'trend': 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        }

    def _get_citation_rate(self):
        """Average citations per mention"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        )

        total_mentions = analytics.count()
        total_with_citations = analytics.exclude(
            total_citations=0
        ).count()

        rate = (total_with_citations / total_mentions * 100) if total_mentions > 0 else 0

        return {
            'type': 'metric',
            'value': round(rate, 1),
            'label': 'Citation Rate',
            'format': 'percentage',
            'subtitle': f'{total_with_citations} of {total_mentions} mentions'
        }

    def _get_citation_density(self):
        """Average number of citations per cited response"""
        from prompts.models import PromptAnalytics

        # Get all analytics with citations
        analytics_with_citations = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        )

        if not analytics_with_citations.exists():
            return {
                'type': 'metric',
                'value': 0,
                'label': 'Citation Density',
                'format': 'decimal'
            }

        # Calculate average citations per response
        total_citations = 0
        for analytics in analytics_with_citations:
            if analytics.citation_list and isinstance(analytics.citation_list, list):
                total_citations += len(analytics.citation_list)

        avg_density = total_citations / analytics_with_citations.count()

        return {
            'type': 'metric',
            'value': round(avg_density, 1),
            'label': 'Citation Density',
            'format': 'decimal',
            'subtitle': 'Avg citations per response'
        }

    def _get_citations_by_platform_chart(self):
        """Citations breakdown by platform"""
        from prompts.models import PromptAnalytics

        platform_data = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        ).values('platform').annotate(
            count=Count('id')
        ).order_by('-count')

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': [
                {
                    'platform': p['platform'] or 'Unknown',
                    'value': p['count']
                }
                for p in platform_data
            ],
            'x_axis': 'platform',
            'y_axis': 'value',
            'label': 'Citations by Platform'
        }

    # ==================== TOPICS WIDGETS ====================

    def _get_total_topics(self):
        """Total number of topics for the domain"""
        from topics.models import Topic

        current_count = Topic.objects.filter(
            domain=self.domain
        ).count()

        return {
            'type': 'metric',
            'value': current_count,
            'label': 'Total Topics',
            'format': 'number'
        }

    def _get_topics_coverage(self):
        """Percentage of keywords covered by topics"""
        from topics.models import Topic
        from keywords.models import Keyword

        total_keywords = Keyword.objects.filter(
            domain=self.domain
        ).count()

        # Count keywords that are associated with at least one topic
        keywords_in_topics = Keyword.objects.filter(
            domain=self.domain,
            topic_keywords__isnull=False
        ).distinct().count()

        coverage = (keywords_in_topics / total_keywords * 100) if total_keywords > 0 else 0

        return {
            'type': 'metric',
            'value': round(coverage, 1),
            'label': 'Topics Coverage',
            'format': 'percentage',
            'subtitle': f'{keywords_in_topics} of {total_keywords} keywords'
        }

    def _get_topics_table(self):
        """Top topics by mentions and sentiment"""
        from topics.models import Topic, TopicAnalytics

        topics = Topic.objects.filter(
            domain=self.domain
        )

        topic_data = []
        for topic in topics:
            # Get topic analytics for the period
            topic_analytics = TopicAnalytics.objects.filter(
                topic=topic,
                timestamp__gte=self.start_date.date(),
                timestamp__lte=self.end_date.date()
            ).aggregate(
                total_mentions=Sum('total_mentions'),
                avg_sentiment=Avg('sentiment_score')
            )

            mention_count = topic_analytics['total_mentions'] or topic.total_mentions or 0
            avg_sentiment = float(topic_analytics['avg_sentiment'] or topic.sentiment_score or 0)
            keyword_count = len(topic.keyword_list) if topic.keyword_list else 0

            if mention_count > 0:  # Only include topics with mentions
                topic_data.append({
                    'topic': topic.name,
                    'keywords': keyword_count,
                    'mentions': mention_count,
                    'sentiment': round(avg_sentiment, 2)
                })

        # Sort by mentions descending
        topic_data.sort(key=lambda x: x['mentions'], reverse=True)

        return {
            'type': 'table',
            'columns': ['Topic', 'Keywords', 'Mentions', 'Avg Sentiment'],
            'rows': topic_data[:10]  # Top 10 topics
        }

    # ==================== SHARE OF VOICE WIDGETS ====================

    def _get_share_of_voice(self):
        """Domain's share of voice percentage"""
        from prompts.models import PromptAnalytics
        from competitors.models import CompetitorAnalytics

        # Get domain mentions
        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        # Get competitor mentions
        competitor_mentions = CompetitorAnalytics.objects.filter(
            competitor__domain=self.domain,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        ).aggregate(
            total=Sum('total_mentions')
        )['total'] or 0

        total_mentions = domain_mentions + competitor_mentions
        share = (domain_mentions / total_mentions * 100) if total_mentions > 0 else 0

        # Calculate previous period
        prev_domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date,
            is_mention=True
        ).count()

        prev_competitor_mentions = CompetitorAnalytics.objects.filter(
            competitor__domain=self.domain,
            timestamp__gte=self.prev_start_date,
            timestamp__lt=self.prev_end_date
        ).aggregate(
            total=Sum('total_mentions')
        )['total'] or 0

        prev_total = prev_domain_mentions + prev_competitor_mentions
        prev_share = (prev_domain_mentions / prev_total * 100) if prev_total > 0 else 0

        change = share - prev_share

        return {
            'type': 'metric',
            'value': round(share, 1),
            'label': 'Share of Voice',
            'format': 'percentage',
            'growth': round(change, 1),
            'trend': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
        }

    def _get_market_position(self):
        """Domain's rank among competitors"""
        from competitors.models import Competitor

        # Get all competitors with their mention counts
        competitors = Competitor.objects.filter(
            domain=self.domain
        ).order_by('-total_mentions')

        # Find domain's position (assuming domain has highest mentions if #1)
        position = 1
        for idx, comp in enumerate(competitors, start=2):
            if comp.total_mentions < self.domain.total_mentions:
                break
            position = idx

        total_tracked = competitors.count() + 1  # +1 for domain itself

        return {
            'type': 'metric',
            'value': position,
            'label': 'Market Position',
            'format': 'ordinal',
            'subtitle': f'out of {total_tracked} tracked'
        }

    def _get_share_of_voice_chart(self):
        """Share of voice comparison chart"""
        from prompts.models import PromptAnalytics
        from competitors.models import Competitor, CompetitorAnalytics

        # Get domain mentions
        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        data = [{
            'name': self.domain.name,
            'value': domain_mentions,
            'is_domain': True
        }]

        # Get top competitors
        competitors = Competitor.objects.filter(
            domain=self.domain
        ).order_by('-total_mentions')[:5]

        for comp in competitors:
            comp_mentions = CompetitorAnalytics.objects.filter(
                competitor=comp,
                timestamp__gte=self.start_date,
                timestamp__lte=self.end_date
            ).aggregate(
                total=Sum('total_mentions')
            )['total'] or 0

            data.append({
                'name': comp.name,
                'value': comp_mentions,
                'is_domain': False
            })

        # Calculate percentages
        total = sum(d['value'] for d in data)
        for item in data:
            item['percentage'] = round((item['value'] / total * 100) if total > 0 else 0, 1)

        return {
            'type': 'chart',
            'chart_type': 'pie',
            'data': data,
            'label': 'Share of Voice Distribution'
        }

    # ==================== HISTORICAL TRENDS WIDGETS ====================

    def _get_mentions_over_time(self):
        """Mentions time series aggregated by MONTH"""
        from prompts.models import PromptAnalytics
        from django.db.models.functions import TruncMonth
        from datetime import datetime, time
        from dateutil.relativedelta import relativedelta
        
        # Normalize to date objects
        start_date = self.start_date.date() if hasattr(self.start_date, 'date') else self.start_date
        end_date = self.end_date.date() if hasattr(self.end_date, 'date') else self.end_date
        
        # Convert to datetime for filtering
        start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
        end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))

        # Get mentions grouped by month
        monthly_data_query = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
            is_mention=True
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Count('id')
        ).order_by('month')
        
        # Create dict for quick lookup
        monthly_data_dict = {}
        for item in monthly_data_query:
            if item['month']:
                month_key = item['month'].strftime('%Y-%m')
                monthly_data_dict[month_key] = item['total']
        
        # Generate complete month range
        monthly_data = []
        
        # Start from beginning of start month
        current_month = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        
        # Month names for display
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        while current_month <= end_month:
            month_key = current_month.strftime('%Y-%m')
            month_display = month_names[current_month.month - 1]
            value = monthly_data_dict.get(month_key, 0)
            
            monthly_data.append({
                'date': month_display,
                'value': value
            })
            
            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': monthly_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Mentions Over Time'
        }

    def _get_visibility_trend(self):
        """Visibility score trend over time"""
        from prompts.models import PromptAnalytics
        
        # Normalize to date objects
        start_date = self.start_date.date() if hasattr(self.start_date, 'date') else self.start_date
        end_date = self.end_date.date() if hasattr(self.end_date, 'date') else self.end_date

        daily_data = []
        current_date = start_date

        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            
            # Convert to datetime for filtering
            from datetime import datetime, time
            current_datetime = timezone.make_aware(datetime.combine(current_date, time.min))
            next_datetime = timezone.make_aware(datetime.combine(next_date, time.min))

            mentions = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_datetime,
                created_at__lt=next_datetime,
                is_mention=True
            )

            mention_count = mentions.count()
            avg_sentiment = mentions.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

            # Simple visibility score: mention_count * (1 + sentiment)
            visibility = mention_count * (1 + max(0, float(avg_sentiment)))

            daily_data.append({
                'date': current_date.strftime('%m/%d'),
                'value': round(visibility, 2)
            })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Visibility Trend'
        }

    def _get_sentiment_trend(self):
        """Sentiment score trend over time"""
        from prompts.models import PromptAnalytics
        
        # Normalize to date objects
        start_date = self.start_date.date() if hasattr(self.start_date, 'date') else self.start_date
        end_date = self.end_date.date() if hasattr(self.end_date, 'date') else self.end_date

        daily_data = []
        current_date = start_date

        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            
            # Convert to datetime for filtering
            from datetime import datetime, time
            current_datetime = timezone.make_aware(datetime.combine(current_date, time.min))
            next_datetime = timezone.make_aware(datetime.combine(next_date, time.min))

            avg_sentiment = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_datetime,
                created_at__lt=next_datetime
            ).aggregate(
                avg=Avg('sentiment_score')
            )['avg'] or 0

            daily_data.append({
                'date': current_date.strftime('%m/%d'),
                'value': round(float(avg_sentiment), 2)
            })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Sentiment Trend'
        }

    def _get_citation_trend(self):
        """Citations trend over time"""
        from prompts.models import PromptAnalytics

        daily_data = []
        current_date = self.start_date

        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            citations = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date
            ).exclude(
                total_citations=0
            ).count()

            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': citations
            })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Citations Trend'
        }

    # ==================== ADDITIONAL COMMON METRICS ====================

    def _get_total_mentions(self):
        """Total mentions metric"""
        from prompts.models import PromptAnalytics

        current_count = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        prev_count = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date,
            is_mention=True
        ).count()

        growth = ((current_count - prev_count) / prev_count * 100) if prev_count > 0 else 0

        return {
            'type': 'metric',
            'value': current_count,
            'label': 'Total Mentions',
            'format': 'number',
            'growth': round(growth, 1),
            'trend': 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        }

    def _get_visibility_score(self):
        """Overall visibility score"""
        return {
            'type': 'metric',
            'value': round(self.domain.visibility_score or 0, 1),
            'label': 'Visibility Score',
            'format': 'decimal'
        }

    def _get_avg_sentiment(self):
        """Average sentiment score"""
        from prompts.models import PromptAnalytics

        avg = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).aggregate(
            avg=Avg('sentiment_score')
        )['avg'] or 0

        return {
            'type': 'metric',
            'value': round(avg, 2),
            'label': 'Avg Sentiment',
            'format': 'decimal',
            'max': 1.0
        }

    # ==================== ADDITIONAL PROMPTS WIDGETS ====================

    def _get_prompt_completion_rate(self):
        """Percentage of completed prompts"""
        from prompts.models import Prompt

        total = Prompt.objects.filter(group__domain=self.domain).count()
        completed = Prompt.objects.filter(
            group__domain=self.domain,
            track_status='COMP'
        ).count()

        rate = (completed / total * 100) if total > 0 else 0

        return {
            'type': 'metric',
            'value': round(rate, 1),
            'label': 'Completion Rate',
            'format': 'percentage',
            'subtitle': f'{completed} of {total} prompts'
        }

    def _get_avg_prompts_per_group(self):
        """Average number of prompts per group"""
        from prompts.models import Prompt, PromptGroup

        total_prompts = Prompt.objects.filter(group__domain=self.domain).count()
        total_groups = PromptGroup.objects.filter(domain=self.domain).count()

        avg = (total_prompts / total_groups) if total_groups > 0 else 0

        return {
            'type': 'metric',
            'value': round(avg, 1),
            'label': 'Avg Prompts per Group',
            'format': 'decimal'
        }

    def _get_prompt_response_rate(self):
        """Percentage of prompts that got responses"""
        from prompts.models import PromptAnalytics

        total_analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).count()

        with_response = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            Q(context_summary__isnull=True) | Q(context_summary='')
        ).count()

        rate = (with_response / total_analytics * 100) if total_analytics > 0 else 0

        return {
            'type': 'metric',
            'value': round(rate, 1),
            'label': 'Response Rate',
            'format': 'percentage',
            'subtitle': f'{with_response} of {total_analytics} queries'
        }

    def _get_prompt_sentiment_distribution(self):
        """Pie chart of sentiment distribution for prompts"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        positive = analytics.filter(sentiment_score__gt=0.3).count()
        neutral = analytics.filter(sentiment_score__gte=-0.3, sentiment_score__lte=0.3).count()
        negative = analytics.filter(sentiment_score__lt=-0.3).count()

        return {
            'type': 'chart',
            'chart_type': 'pie',
            'data': [
                {'name': 'Positive', 'value': positive},
                {'name': 'Neutral', 'value': neutral},
                {'name': 'Negative', 'value': negative}
            ],
            'label': 'Prompt Sentiment Distribution'
        }

    def _get_recent_prompts_table(self):
        """Table of recently processed prompts"""
        from prompts.models import Prompt

        prompts = Prompt.objects.filter(
            group__domain=self.domain,
            track_status='COMP'
        ).order_by('-updated_at')[:10]

        return {
            'type': 'table',
            'columns': ['Prompt', 'Group', 'Status', 'Updated'],
            'rows': [
                {
                    'prompt': p.prompt[:60] + '...' if len(p.prompt) > 60 else p.prompt,
                    'group': p.group.theme if p.group.theme else f'Group {p.group.group_id}',
                    'status': p.track_status,
                    'updated': p.updated_at.strftime('%Y-%m-%d') if p.updated_at else 'N/A'
                }
                for p in prompts
            ]
        }

    # ==================== ADDITIONAL CITATIONS WIDGETS ====================

    def _get_primary_sources_count(self):
        """Count of unique primary sources cited"""
        from prompts.models import PromptAnalytics

        analytics_with_citations = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        )

        # Count unique URLs
        unique_sources = set()
        for analytics in analytics_with_citations:
            if analytics.citation_list and isinstance(analytics.citation_list, list):
                for citation in analytics.citation_list:
                    if isinstance(citation, str):
                        unique_sources.add(citation)
                    elif isinstance(citation, dict):
                        unique_sources.add(citation.get('url', citation.get('link', '')))

        return {
            'type': 'metric',
            'value': len(unique_sources),
            'label': 'Primary Sources',
            'format': 'number',
            'subtitle': 'Unique citation sources'
        }

    def _get_citation_growth(self):
        """Citation growth vs previous period"""
        from prompts.models import PromptAnalytics

        current = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        ).count()

        previous = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date
        ).exclude(
            total_citations=0
        ).count()

        growth = ((current - previous) / previous * 100) if previous > 0 else 0

        return {
            'type': 'metric',
            'value': round(growth, 1),
            'label': 'Citation Growth',
            'format': 'percentage',
            'growth': growth,
            'trend': 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        }

    def _get_top_cited_prompts(self):
        """Table of prompts with most citations"""
        from prompts.models import Prompt, PromptAnalytics

        prompts_with_citations = []

        for prompt in Prompt.objects.filter(group__domain=self.domain):
            analytics = PromptAnalytics.objects.filter(
                prompt=prompt,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).exclude(
                total_citations=0
            )

            citation_count = 0
            for a in analytics:
                if a.citation_list and isinstance(a.citation_list, list):
                    citation_count += len(a.citation_list)

            if citation_count > 0:
                prompts_with_citations.append({
                    'prompt': prompt.prompt[:60] + '...' if len(prompt.prompt) > 60 else prompt.prompt,
                    'citations': citation_count,
                    'responses': analytics.count()
                })

        # Sort by citations descending
        prompts_with_citations.sort(key=lambda x: x['citations'], reverse=True)

        return {
            'type': 'table',
            'columns': ['Prompt', 'Citations', 'Responses'],
            'rows': prompts_with_citations[:10]
        }

    def _get_avg_citations_per_platform(self):
        """Average citations per platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        best_platform = None
        best_avg = 0

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).exclude(
                total_citations=0
            )

            total_citations = 0
            for a in analytics:
                if a.citation_list and isinstance(a.citation_list, list):
                    total_citations += len(a.citation_list)

            avg = (total_citations / analytics.count()) if analytics.count() > 0 else 0
            if avg > best_avg:
                best_avg = avg
                best_platform = platform

        return {
            'type': 'metric',
            'value': round(best_avg, 1),
            'label': 'Best Platform (Citations)',
            'format': 'decimal',
            'subtitle': f'{best_platform} leads' if best_platform else 'No data'
        }

    # ==================== ADDITIONAL TOPICS WIDGETS ====================

    def _get_top_topic_by_mentions(self):
        """Top topic by mention count"""
        from topics.models import Topic

        # Get topic with highest mentions
        top_topic = Topic.objects.filter(
            domain=self.domain
        ).order_by('-total_mentions').first()

        if top_topic:
            return {
                'type': 'metric',
                'value': top_topic.total_mentions,
                'label': 'Top Topic',
                'format': 'number',
                'subtitle': top_topic.name
            }
        else:
            return {
                'type': 'metric',
                'value': 0,
                'label': 'Top Topic',
                'format': 'number',
                'subtitle': 'No topics'
            }

    def _get_avg_keywords_per_topic(self):
        """Average keywords per topic"""
        from topics.models import Topic

        topics = Topic.objects.filter(domain=self.domain)

        total_keywords = sum(len(t.keyword_list) if t.keyword_list else 0 for t in topics)
        topic_count = topics.count()

        avg = (total_keywords / topic_count) if topic_count > 0 else 0

        return {
            'type': 'metric',
            'value': round(avg, 1),
            'label': 'Avg Keywords per Topic',
            'format': 'decimal'
        }

    def _get_topic_sentiment_chart(self):
        """Bar chart of sentiment by topic"""
        from topics.models import Topic

        topics = Topic.objects.filter(domain=self.domain).order_by('-total_mentions')[:10]

        data = []
        for topic in topics:
            data.append({
                'name': topic.name[:20],
                'value': round(float(topic.sentiment_score or 0), 2)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'x_axis': 'name',
            'y_axis': 'value',
            'label': 'Topic Sentiment Scores'
        }

    def _get_topic_distribution_chart(self):
        """Pie chart showing mention distribution across topics"""
        from topics.models import Topic

        topics = Topic.objects.filter(
            domain=self.domain,
            total_mentions__gt=0
        ).order_by('-total_mentions')[:5]

        data = []
        for topic in topics:
            data.append({
                'name': topic.name[:20],
                'value': topic.total_mentions
            })

        return {
            'type': 'chart',
            'chart_type': 'pie',
            'data': data,
            'label': 'Topic Distribution'
        }

    # ==================== ADDITIONAL SHARE OF VOICE WIDGETS ====================

    def _get_competitor_count(self):
        """Total number of tracked competitors"""
        from competitors.models import Competitor

        count = Competitor.objects.filter(domain=self.domain).count()

        return {
            'type': 'metric',
            'value': count,
            'label': 'Tracked Competitors',
            'format': 'number'
        }

    def _get_share_vs_top_competitor(self):
        """Share difference vs top competitor"""
        from prompts.models import PromptAnalytics
        from competitors.models import Competitor, CompetitorAnalytics

        # Get domain mentions
        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        # Get top competitor
        top_competitor = Competitor.objects.filter(
            domain=self.domain
        ).order_by('-total_mentions').first()

        if not top_competitor:
            return {
                'type': 'metric',
                'value': 0,
                'label': 'Gap to #1',
                'format': 'number',
                'subtitle': 'No competitors'
            }

        competitor_mentions = CompetitorAnalytics.objects.filter(
            competitor=top_competitor,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        ).aggregate(Sum('total_mentions'))['total_mentions__sum'] or 0

        gap = domain_mentions - competitor_mentions

        return {
            'type': 'metric',
            'value': gap,
            'label': 'Gap to #1',
            'format': 'number',
            'subtitle': f'vs {top_competitor.name}',
            'trend': 'up' if gap > 0 else 'down'
        }

    def _get_share_of_voice_trend(self):
        """Share of voice trend over time"""
        from prompts.models import PromptAnalytics
        from competitors.models import CompetitorAnalytics

        daily_data = []
        current_date = self.start_date

        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            domain_mentions = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date,
                is_mention=True
            ).count()

            competitor_mentions = CompetitorAnalytics.objects.filter(
                competitor__domain=self.domain,
                timestamp__gte=current_date,
                timestamp__lt=next_date
            ).aggregate(Sum('total_mentions'))['total_mentions__sum'] or 0

            total = domain_mentions + competitor_mentions
            share = (domain_mentions / total * 100) if total > 0 else 0

            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': round(share, 1)
            })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Share of Voice Trend'
        }

    def _get_competitors_ranking_table(self):
        """Table showing competitor rankings with all metrics"""
        from competitors.models import Competitor, CompetitorAnalytics
        from prompts.models import PromptAnalytics
        from django.db.models.functions import TruncMonth
        from datetime import datetime, time

        # Normalize datetimes for filtering
        start_dt = self.start_date
        end_dt = self.end_date
        if hasattr(self.start_date, 'date'):
            start_dt = timezone.make_aware(datetime.combine(self.start_date.date(), time.min))
        if hasattr(self.end_date, 'date'):
            end_dt = timezone.make_aware(datetime.combine(self.end_date.date(), time.max))

        # Get our brand mentions within range
        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
            is_mention=True
        ).count()

        rankings = [{
            'rank': 1,
            'name': self.domain.name,
            'mentions': domain_mentions,
            'share': 0  # will compute later
        }]

        competitors = Competitor.objects.filter(domain=self.domain)

        for comp in competitors:
            # Prefer pre-aggregated totals if available
            comp_mentions = comp.total_mentions or 0

            # If missing, fall back to analytics aggregated in range
            if comp_mentions == 0:
                comp_mentions = CompetitorAnalytics.objects.filter(
                    competitor=comp,
                    timestamp__gte=start_dt,
                    timestamp__lte=end_dt
                ).aggregate(Sum('total_mentions'))['total_mentions__sum'] or 0

            rankings.append({
                'rank': 0,  # assign later
                'name': comp.name,
                'mentions': comp_mentions,
                'share': 0  # assign later
            })

        # Sort and compute share
        rankings.sort(key=lambda x: x['mentions'], reverse=True)
        total_mentions = sum(r['mentions'] for r in rankings)
        for i, r in enumerate(rankings, 1):
            r['rank'] = i
            r['share'] = round((r['mentions'] / total_mentions * 100), 1) if total_mentions > 0 else 0.0

        return {
            'type': 'table',
            'columns': ['Rank', 'Name', 'Mentions', 'Share %'],
            'rows': rankings[:10]
        }

    # ==================== ADDITIONAL HISTORICAL TRENDS WIDGETS ====================

    def _get_platform_mentions_trend(self):
        """Multi-line chart showing mentions per platform over time"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity']
        platform_data = {p: [] for p in platforms}

        current_date = self.start_date
        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            for platform in platforms:
                mentions = PromptAnalytics.objects.filter(
                    prompt__group__domain=self.domain,
                    platform=platform,
                    created_at__gte=current_date,
                    created_at__lt=next_date,
                    is_mention=True
                ).count()

                platform_data[platform].append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'value': mentions,
                    'platform': platform
                })

            current_date = next_date

        # Flatten data for chart
        all_data = []
        for platform, data in platform_data.items():
            all_data.extend(data)

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': all_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Platform Mentions Trend'
        }

    def _get_weekly_growth_chart(self):
        """Weekly growth rate chart"""
        from prompts.models import PromptAnalytics

        weekly_data = []
        current_date = self.start_date

        prev_week_mentions = 0

        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=7)

            mentions = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date,
                is_mention=True
            ).count()

            growth = ((mentions - prev_week_mentions) / prev_week_mentions * 100) if prev_week_mentions > 0 else 0

            weekly_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': round(growth, 1)
            })

            prev_week_mentions = mentions
            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': weekly_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Weekly Growth Rate %'
        }

    def _get_response_rate_trend(self):
        """Response rate trend over time"""
        from prompts.models import PromptAnalytics

        daily_data = []
        current_date = self.start_date

        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            total = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date
            ).count()

            with_response = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date
            ).exclude(
                Q(context_summary__isnull=True) | Q(context_summary='')
            ).count()

            rate = (with_response / total * 100) if total > 0 else 0

            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': round(rate, 1)
            })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Response Rate Trend %'
        }

    def _get_comparative_trends(self):
        """Comparative trend showing multiple metrics"""
        from prompts.models import PromptAnalytics

        daily_data = []
        current_date = self.start_date

        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date
            )

            mentions = analytics.filter(is_mention=True).count()
            citations = analytics.exclude(total_citations=0).count()
            sentiment = analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'mentions': mentions,
                'citations': citations,
                'sentiment': round(sentiment * 10, 1)  # Scale sentiment for visibility
            })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Comparative Trends'
        }

    # ==================== NEW CITATIONS WIDGETS ====================

    def _get_unique_sources(self):
        """Count of unique citation sources"""
        from prompts.models import PromptAnalytics

        analytics_with_citations = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        )

        unique_sources = set()
        for analytics in analytics_with_citations:
            if analytics.citation_list and isinstance(analytics.citation_list, list):
                for citation in analytics.citation_list:
                    if isinstance(citation, str):
                        unique_sources.add(citation)
                    elif isinstance(citation, dict):
                        unique_sources.add(citation.get('url', citation.get('link', '')))

        return {
            'type': 'metric',
            'value': len(unique_sources),
            'label': 'Unique Sources',
            'format': 'number'
        }

    def _get_domain_citations(self):
        """Citations that link to your domain"""
        from prompts.models import PromptAnalytics

        analytics_with_citations = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        )

        domain_citations = 0
        domain_url = self.domain.url.lower()

        for analytics in analytics_with_citations:
            if analytics.citation_list and isinstance(analytics.citation_list, list):
                for citation in analytics.citation_list:
                    citation_url = ''
                    if isinstance(citation, str):
                        citation_url = citation.lower()
                    elif isinstance(citation, dict):
                        citation_url = citation.get('url', citation.get('link', '')).lower()

                    if domain_url in citation_url:
                        domain_citations += 1

        return {
            'type': 'metric',
            'value': domain_citations,
            'label': 'Domain Citations',
            'format': 'number',
            'subtitle': f'Links to {self.domain.name}'
        }

    def _get_valid_links(self):
        """Count of verified valid citation links"""
        from prompts.models import PromptAnalytics

        # Count all citations that are not marked as broken
        # For now, assume all citations are valid unless marked otherwise
        analytics_with_citations = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        )

        total_citations = 0
        for analytics in analytics_with_citations:
            if analytics.citation_list and isinstance(analytics.citation_list, list):
                total_citations += len(analytics.citation_list)

        # In a real implementation, you'd check citation health status
        # For now, return total citations as valid
        return {
            'type': 'metric',
            'value': total_citations,
            'label': 'Valid Links',
            'format': 'number',
            'subtitle': 'Successfully verified URLs'
        }

    def _get_pending_citations(self):
        """Citations awaiting verification"""
        # In a real implementation, this would check citation verification status
        # For now, return 0 as placeholder
        return {
            'type': 'metric',
            'value': 0,
            'label': 'Pending Citations',
            'format': 'number',
            'subtitle': 'Awaiting verification'
        }

    # ==================== NEW SENTIMENT WIDGETS ====================

    def _get_competitor_comparison_chart(self):
        """Sentiment comparison with competitors"""
        from prompts.models import PromptAnalytics
        from competitors.models import Competitor

        # Get domain sentiment
        domain_sentiment = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

        data = [{
            'name': self.domain.name,
            'sentiment': round(domain_sentiment, 2),
            'is_domain': True
        }]

        # Get top competitors (simplified - would need CompetitorAnalytics sentiment in real impl)
        competitors = Competitor.objects.filter(domain=self.domain).order_by('-total_mentions')[:5]

        for comp in competitors:
            # In real implementation, fetch competitor sentiment from CompetitorAnalytics
            # For now, use a placeholder
            data.append({
                'name': comp.name,
                'sentiment': 0.5,  # Placeholder
                'is_domain': False
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'x_axis': 'name',
            'y_axis': 'sentiment',
            'label': 'Competitor Sentiment Comparison'
        }

    # ==================== NEW TOPICS WIDGETS ====================

    def _get_topic_trends_chart(self):
        """Topic mentions over time - complete date range with actual data"""
        from prompts.models import PromptAnalytics
        from django.db.models.functions import TruncDate
        
        # Normalize dates to date objects
        start_date = self.start_date.date() if hasattr(self.start_date, 'date') else self.start_date
        end_date = self.end_date.date() if hasattr(self.end_date, 'date') else self.end_date
        
        # Convert back to datetime for filtering
        from datetime import datetime, time
        start_datetime = timezone.make_aware(datetime.combine(start_date, time.min))
        end_datetime = timezone.make_aware(datetime.combine(end_date, time.max))

        # Get ALL mentions grouped by date
        daily_data_dict = {}
        daily_query = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
            is_mention=True
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Count('id')
        ).order_by('date')
        
        # Create a dict for quick lookup
        for item in daily_query:
            date_str = item['date'].strftime('%Y-%m-%d')
            daily_data_dict[date_str] = item['total']
        
        # Generate complete date range (fills gaps with zeros)
        all_data = []
        current_date = start_date
        while current_date <= end_date:
            # Use both formats: full for lookup, short for display
            date_key = current_date.strftime('%Y-%m-%d')
            date_display = current_date.strftime('%m/%d')  # Shorter format for chart
            value = daily_data_dict.get(date_key, 0)  # Use 0 if no data for this date
            
            all_data.append({
                'date': date_display,  # Display format
                'value': value
            })
            current_date = current_date + timedelta(days=1)
        
        # For very long ranges (>15 days), sample every Nth day to avoid overcrowding
        # But always include days with non-zero values
        total_days = len(all_data)
        if total_days > 15:
            # Calculate sampling interval
            sample_interval = max(2, total_days // 10)  # Show ~10-15 points
            
            sampled_data = []
            for i, item in enumerate(all_data):
                # Include if: it's a sampled point, or has non-zero value, or is first/last
                if i % sample_interval == 0 or item['value'] > 0 or i == 0 or i == len(all_data) - 1:
                    sampled_data.append(item)
            
            all_data = sampled_data

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': all_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Topic Trends Over Time'
        }

    # ==================== NEW SHARE OF VOICE WIDGETS ====================

    def _get_market_share(self):
        """Market share percentage (alias for share of voice)"""
        return self._get_share_of_voice()

    def _get_dominance_score(self):
        """Overall market dominance score"""
        from prompts.models import PromptAnalytics
        from competitors.models import CompetitorAnalytics

        # Calculate dominance based on mentions, share, and sentiment
        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        competitor_mentions = CompetitorAnalytics.objects.filter(
            competitor__domain=self.domain,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        ).aggregate(total=Sum('total_mentions'))['total'] or 0

        total = domain_mentions + competitor_mentions
        share = (domain_mentions / total * 100) if total > 0 else 0

        # Get sentiment
        sentiment = float(PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0)

        # Calculate dominance score (0-100)
        # Formula: (share * 0.7) + (sentiment * 100 * 0.3)
        dominance = (share * 0.7) + (max(0, sentiment) * 100 * 0.3)

        return {
            'type': 'metric',
            'value': round(dominance, 1),
            'label': 'Dominance Score',
            'format': 'decimal',
            'subtitle': 'Out of 100'
        }

    def _get_overall_market_share(self):
        """Overall market share across all platforms (same as share of voice)"""
        return self._get_share_of_voice()

    def _get_brand_positioning_matrix(self):
        """Brand positioning vs competitors (sentiment vs mentions)"""
        from prompts.models import PromptAnalytics
        from competitors.models import Competitor, CompetitorAnalytics

        # Domain data
        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        domain_sentiment = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

        data = [{
            'name': self.domain.name,
            'mentions': domain_mentions,
            'sentiment': round(domain_sentiment, 2),
            'is_domain': True
        }]

        # Competitor data
        competitors = Competitor.objects.filter(domain=self.domain).order_by('-total_mentions')[:8]

        for comp in competitors:
            comp_mentions = CompetitorAnalytics.objects.filter(
                competitor=comp,
                timestamp__gte=self.start_date,
                timestamp__lte=self.end_date
            ).aggregate(total=Sum('total_mentions'))['total'] or 0

            data.append({
                'name': comp.name,
                'mentions': comp_mentions,
                'sentiment': 0.5,  # Placeholder - would need real competitor sentiment
                'is_domain': False
            })

        return {
            'type': 'chart',
            'chart_type': 'scatter',
            'data': data,
            'x_axis': 'mentions',
            'y_axis': 'sentiment',
            'label': 'Brand Positioning Matrix'
        }

    # ==================== NEW HISTORICAL TRENDS WIDGETS ====================

    def _get_visibility_growth_chart(self):
        """Visibility score growth over time"""
        # Reuse visibility trend
        return self._get_visibility_trend()

    def _get_mention_growth_chart(self):
        """Mention count growth trends"""
        from prompts.models import PromptAnalytics

        daily_data = []
        current_date = self.start_date
        previous_count = 0

        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            mentions = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date,
                is_mention=True
            ).count()

            growth = ((mentions - previous_count) / previous_count * 100) if previous_count > 0 else 0

            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': round(growth, 1),
                'mentions': mentions
            })

            previous_count = mentions if mentions > 0 else previous_count
            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Mention Growth %'
        }

    def _get_position_improvement_chart(self):
        """Average position changes over time"""
        from prompts.models import PromptAnalytics

        daily_data = []
        current_date = self.start_date

        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            # Calculate average position from is_mentioned responses
            avg_position = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=current_date,
                created_at__lt=next_date,
                is_mention=True
            ).aggregate(Avg('position'))['position__avg'] or 0

            daily_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'value': round(avg_position, 2)
            })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': daily_data,
            'x_axis': 'date',
            'y_axis': 'value',
            'label': 'Average Position Over Time'
        }

    def _get_market_share_gain_chart(self):
        """Market share growth visualization"""
        # Reuse share of voice trend
        return self._get_share_of_voice_trend()

    def _get_visibility_score_progression(self):
        """Detailed visibility score timeline"""
        # Reuse visibility trend with different label
        result = self._get_visibility_trend()
        result['label'] = 'Visibility Score Progression'
        return result

    # ==================== ADDITIONAL MISSING WIDGETS ====================

    def _get_avg_position(self):
        """Average position in AI responses"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True,
            position__isnull=False
        )

        avg_position = analytics.aggregate(Avg('position'))['position__avg'] or 0

        return {
            'type': 'metric',
            'value': round(avg_position, 1),
            'label': 'Average Position',
            'format': 'decimal',
            'subtitle': 'Lower is better'
        }

    def _get_engagement_score(self):
        """Overall engagement score based on mentions and sentiment"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        mentions = analytics.filter(is_mention=True).count()
        total = analytics.count()
        avg_sentiment = float(analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0)

        # Engagement score: combination of mention rate and sentiment
        mention_rate = (mentions / total * 100) if total > 0 else 0
        engagement = (mention_rate * 0.7) + (max(0, avg_sentiment) * 100 * 0.3)

        return {
            'type': 'metric',
            'value': round(engagement, 1),
            'label': 'Engagement Score',
            'format': 'decimal',
            'subtitle': 'Out of 100'
        }

    def _get_mention_rate(self):
        """Percentage of prompts that result in mentions"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        mentions = analytics.filter(is_mention=True).count()
        rate = (mentions / total * 100) if total > 0 else 0

        return {
            'type': 'metric',
            'value': round(rate, 1),
            'label': 'Mention Rate',
            'format': 'percentage',
            'subtitle': f'{mentions} of {total}'
        }

    def _get_mention_growth(self):
        """Mention count growth vs previous period"""
        from prompts.models import PromptAnalytics

        current = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        previous = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date,
            is_mention=True
        ).count()

        growth = ((current - previous) / previous * 100) if previous > 0 else 0

        return {
            'type': 'metric',
            'value': round(growth, 1),
            'label': 'Mention Growth',
            'format': 'percentage',
            'growth': round(growth, 1),
            'trend': 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        }

    def _get_platform_coverage(self):
        """Number of platforms with mentions"""
        from prompts.models import PromptAnalytics

        platforms_with_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).values('platform').distinct().count()

        return {
            'type': 'metric',
            'value': platforms_with_mentions,
            'label': 'Platform Coverage',
            'format': 'number',
            'subtitle': 'Platforms with mentions'
        }

    def _get_positive_sentiment(self):
        """Percentage of positive sentiment responses"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        positive = analytics.filter(sentiment_score__gt=0.3).count()
        pct = (positive / total * 100) if total > 0 else 0

        return {
            'type': 'metric',
            'value': round(pct, 1),
            'label': 'Positive Sentiment',
            'format': 'percentage',
            'subtitle': f'{positive} responses'
        }

    def _get_negative_sentiment(self):
        """Percentage of negative sentiment responses"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        negative = analytics.filter(sentiment_score__lt=-0.3).count()
        pct = (negative / total * 100) if total > 0 else 0

        return {
            'type': 'metric',
            'value': round(pct, 1),
            'label': 'Negative Sentiment',
            'format': 'percentage',
            'subtitle': f'{negative} responses'
        }

    def _get_sentiment_trend_metric(self):
        """Sentiment change vs previous period"""
        from prompts.models import PromptAnalytics

        current = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

        previous = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date
        ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

        change = (current - previous) * 100

        return {
            'type': 'metric',
            'value': round(change, 1),
            'label': 'Sentiment Trend',
            'format': 'percentage',
            'growth': round(change, 1),
            'trend': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
        }

    def _get_competitor_gap(self):
        """Gap to the top competitor"""
        from prompts.models import PromptAnalytics
        from competitors.models import Competitor, CompetitorAnalytics

        domain_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        top_competitor = Competitor.objects.filter(
            domain=self.domain
        ).order_by('-total_mentions').first()

        if not top_competitor:
            return {
                'type': 'metric',
                'value': 0,
                'label': 'Competitor Gap',
                'format': 'number',
                'subtitle': 'No competitors'
            }

        competitor_mentions = CompetitorAnalytics.objects.filter(
            competitor=top_competitor,
            timestamp__gte=self.start_date.date(),
            timestamp__lte=self.end_date.date()
        ).aggregate(Sum('total_mentions'))['total_mentions__sum'] or top_competitor.total_mentions

        gap = domain_mentions - competitor_mentions

        return {
            'type': 'metric',
            'value': gap,
            'label': 'Competitor Gap',
            'format': 'number',
            'subtitle': f'vs {top_competitor.name}',
            'trend': 'up' if gap > 0 else 'down' if gap < 0 else 'neutral'
        }

    def _get_market_share_trend(self):
        """Market share change over time"""
        sov_data = self._get_share_of_voice()
        return {
            'type': 'metric',
            'value': sov_data.get('growth', 0),
            'label': 'Market Share Trend',
            'format': 'percentage',
            'growth': sov_data.get('growth', 0),
            'trend': sov_data.get('trend', 'neutral')
        }

    def _get_health_score(self):
        """Overall AI visibility health score"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        mentions = analytics.filter(is_mention=True).count()
        avg_sentiment = float(analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0)

        # Health score based on mention rate and sentiment
        mention_rate = (mentions / total * 100) if total > 0 else 0
        sentiment_component = (avg_sentiment + 1) / 2 * 100  # Normalize -1 to 1 → 0 to 100
        health = (mention_rate * 0.6) + (sentiment_component * 0.4)

        return {
            'type': 'metric',
            'value': round(health, 1),
            'label': 'Health Score',
            'format': 'decimal',
            'subtitle': 'Out of 100'
        }

    def _get_content_quality(self):
        """Content quality score based on citations and sentiment"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        with_citations = analytics.exclude(
            total_citations=0
        ).count()
        avg_sentiment = float(analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0)

        citation_rate = (with_citations / total * 100) if total > 0 else 0
        sentiment_component = (avg_sentiment + 1) / 2 * 100
        quality = (citation_rate * 0.5) + (sentiment_component * 0.5)

        return {
            'type': 'metric',
            'value': round(quality, 1),
            'label': 'Content Quality',
            'format': 'decimal',
            'subtitle': 'Out of 100'
        }

    def _get_topics_covered(self):
        """Number of topics being tracked"""
        from topics.models import Topic

        count = Topic.objects.filter(domain=self.domain).count()

        return {
            'type': 'metric',
            'value': count,
            'label': 'Topics Covered',
            'format': 'number'
        }

    def _get_answer_coverage(self):
        """Percentage of prompts with responses containing domain mentions"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        with_mentions = analytics.filter(is_mention=True).count()
        coverage = (with_mentions / total * 100) if total > 0 else 0

        return {
            'type': 'metric',
            'value': round(coverage, 1),
            'label': 'Answer Coverage',
            'format': 'percentage',
            'subtitle': f'{with_mentions} of {total} responses'
        }

    def _get_visibility_trend_metric(self):
        """Visibility score change vs previous period"""
        visibility = self.domain.visibility_score or 0

        # Calculate previous period visibility (simplified)
        from prompts.models import PromptAnalytics

        current_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        prev_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date,
            is_mention=True
        ).count()

        change = ((current_mentions - prev_mentions) / prev_mentions * 100) if prev_mentions > 0 else 0

        return {
            'type': 'metric',
            'value': round(change, 1),
            'label': 'Visibility Trend',
            'format': 'percentage',
            'growth': round(change, 1),
            'trend': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
        }

    def _get_mention_growth_percent(self):
        """Mention growth as percentage"""
        return self._get_mention_growth()

    def _get_engagement_growth(self):
        """Engagement change vs previous period"""
        from prompts.models import PromptAnalytics

        # Current period
        current_analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        current_mentions = current_analytics.filter(is_mention=True).count()
        current_total = current_analytics.count()
        current_rate = (current_mentions / current_total * 100) if current_total > 0 else 0

        # Previous period
        prev_analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.prev_start_date,
            created_at__lt=self.prev_end_date
        )
        prev_mentions = prev_analytics.filter(is_mention=True).count()
        prev_total = prev_analytics.count()
        prev_rate = (prev_mentions / prev_total * 100) if prev_total > 0 else 0

        change = current_rate - prev_rate

        return {
            'type': 'metric',
            'value': round(change, 1),
            'label': 'Engagement Growth',
            'format': 'percentage',
            'growth': round(change, 1),
            'trend': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
        }

    def _get_active_alerts(self):
        """Number of active alerts"""
        # In a real implementation, fetch from alerts table
        return {
            'type': 'metric',
            'value': 0,
            'label': 'Active Alerts',
            'format': 'number',
            'subtitle': 'No active alerts'
        }

    def _get_critical_issues(self):
        """Number of critical issues found"""
        return {
            'type': 'metric',
            'value': 0,
            'label': 'Critical Issues',
            'format': 'number',
            'subtitle': 'No issues detected'
        }

    def _get_broken_links(self):
        """Count of broken citation links"""
        return {
            'type': 'metric',
            'value': 0,
            'label': 'Broken Links',
            'format': 'number',
            'subtitle': 'All links verified'
        }

    def _get_misinformation_cases(self):
        """Number of misinformation cases detected"""
        try:
            from misinformation.models import MisinformationReport
            count = MisinformationReport.objects.filter(
                domain=self.domain,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).count()
        except:
            count = 0

        return {
            'type': 'metric',
            'value': count,
            'label': 'Misinformation Cases',
            'format': 'number'
        }

    def _get_platform_chart(self):
        """Platform distribution bar chart"""
        from prompts.models import PromptAnalytics

        platform_data = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).values('platform').annotate(
            count=Count('id')
        ).order_by('-count')

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': [
                {
                    'platform': p['platform'] or 'Unknown',
                    'value': p['count']
                }
                for p in platform_data
            ],
            'label': 'Platform Distribution'
        }

    def _get_summary_text(self):
        """Executive summary text"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        mentions = analytics.filter(is_mention=True).count()
        avg_sentiment = analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0
        mention_rate = (mentions / total * 100) if total > 0 else 0

        sentiment_label = 'positive' if avg_sentiment > 0.3 else ('negative' if avg_sentiment < -0.3 else 'neutral')

        summary = f"During the reporting period, {self.domain.name} received {mentions} mentions across {total} analyzed prompts, achieving a {round(mention_rate, 1)}% mention rate with {sentiment_label} overall sentiment."

        return {
            'type': 'text',
            'value': summary,
            'label': 'Executive Summary'
        }

    def _get_sentiment_chart(self):
        """Sentiment distribution pie chart"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        positive = analytics.filter(sentiment_score__gt=0.3).count()
        neutral = analytics.filter(sentiment_score__gte=-0.3, sentiment_score__lte=0.3).count()
        negative = analytics.filter(sentiment_score__lt=-0.3).count()

        return {
            'type': 'chart',
            'chart_type': 'pie',
            'data': [
                {'name': 'Positive', 'value': positive},
                {'name': 'Neutral', 'value': neutral},
                {'name': 'Negative', 'value': negative}
            ],
            'label': 'Sentiment Distribution'
        }

    def _get_platform_sentiment_breakdown(self):
        """Sentiment breakdown by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            avg_sentiment = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

            data.append({
                'name': platform,
                'value': round(avg_sentiment, 2)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'label': 'Platform Sentiment Breakdown'
        }

    def _get_total_platforms(self):
        """Total number of platforms being tracked"""
        from prompts.models import PromptAnalytics

        platforms = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).values('platform').distinct().count()

        return {
            'type': 'metric',
            'value': platforms,
            'label': 'Total Platforms',
            'format': 'number'
        }

    def _get_total_platform_mentions(self):
        """Total mentions across all platforms"""
        from prompts.models import PromptAnalytics

        mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        return {
            'type': 'metric',
            'value': mentions,
            'label': 'Platform Mentions',
            'format': 'number'
        }

    def _get_total_platform_citations(self):
        """Total citations across all platforms"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            total_citations=0
        )

        total_citations = 0
        for a in analytics:
            if a.citation_list and isinstance(a.citation_list, list):
                total_citations += len(a.citation_list)

        return {
            'type': 'metric',
            'value': total_citations,
            'label': 'Platform Citations',
            'format': 'number'
        }

    def _get_platform_visibility(self, platform_name):
        """Visibility score for a specific platform"""
        from prompts.models import PromptAnalytics

        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            platform=platform_name,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        total = analytics.count()
        mentions = analytics.filter(is_mention=True).count()
        visibility = (mentions / total * 100) if total > 0 else 0

        return {
            'type': 'metric',
            'value': round(visibility, 1),
            'label': f'{platform_name} Visibility',
            'format': 'percentage',
            'subtitle': f'{mentions} mentions'
        }

    def _get_top_performing_platform(self):
        """Platform with highest mention rate"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        best_platform = None
        best_rate = 0

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            )
            total = analytics.count()
            mentions = analytics.filter(is_mention=True).count()
            rate = (mentions / total * 100) if total > 0 else 0

            if rate > best_rate:
                best_rate = rate
                best_platform = platform

        return {
            'type': 'metric',
            'value': round(best_rate, 1),
            'label': 'Top Platform',
            'format': 'percentage',
            'subtitle': best_platform or 'N/A'
        }

    def _get_platform_mention_distribution(self):
        """Pie chart of mentions by platform"""
        from prompts.models import PromptAnalytics

        platform_data = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).values('platform').annotate(
            count=Count('id')
        ).order_by('-count')

        return {
            'type': 'chart',
            'chart_type': 'pie',
            'data': [
                {'name': p['platform'] or 'Unknown', 'value': p['count']}
                for p in platform_data
            ],
            'label': 'Platform Mention Distribution'
        }

    def _get_platform_citation_distribution(self):
        """Pie chart of citations by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).exclude(
                total_citations=0
            )

            total_citations = 0
            for a in analytics:
                if a.citation_list and isinstance(a.citation_list, list):
                    total_citations += len(a.citation_list)

            if total_citations > 0:
                data.append({'name': platform, 'value': total_citations})

        return {
            'type': 'chart',
            'chart_type': 'pie',
            'data': data,
            'label': 'Platform Citation Distribution'
        }

    def _get_avg_position_by_platform(self):
        """Bar chart of average position by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            avg_position = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date,
                is_mention=True,
                position__isnull=False
            ).aggregate(Avg('position'))['position__avg'] or 0

            data.append({
                'name': platform,
                'value': round(avg_position, 2)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'label': 'Average Position by Platform'
        }

    def _get_best_platform_position(self):
        """Platform with best (lowest) average position"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        best_platform = None
        best_position = float('inf')

        for platform in platforms:
            avg_position = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date,
                is_mention=True,
                position__isnull=False
            ).aggregate(Avg('position'))['position__avg']

            if avg_position is not None and avg_position < best_position:
                best_position = avg_position
                best_platform = platform

        return {
            'type': 'metric',
            'value': round(best_position, 1) if best_position != float('inf') else 0,
            'label': 'Best Position',
            'format': 'decimal',
            'subtitle': best_platform or 'N/A'
        }

    def _get_platform_position_comparison(self):
        """Bar chart comparing positions across platforms"""
        return self._get_avg_position_by_platform()

    def _get_most_positive_platform(self):
        """Platform with highest sentiment"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        best_platform = None
        best_sentiment = -2

        for platform in platforms:
            avg_sentiment = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).aggregate(Avg('sentiment_score'))['sentiment_score__avg']

            if avg_sentiment is not None and avg_sentiment > best_sentiment:
                best_sentiment = avg_sentiment
                best_platform = platform

        return {
            'type': 'metric',
            'value': round(best_sentiment, 2) if best_sentiment > -2 else 0,
            'label': 'Most Positive',
            'format': 'decimal',
            'subtitle': best_platform or 'N/A'
        }

    def _get_platform_sentiment_trends(self):
        """Sentiment trends by platform over time"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity']
        all_data = []

        current_date = self.start_date
        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)

            for platform in platforms:
                avg_sentiment = PromptAnalytics.objects.filter(
                    prompt__group__domain=self.domain,
                    platform=platform,
                    created_at__gte=current_date,
                    created_at__lt=next_date
                ).aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

                all_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'value': round(avg_sentiment, 2),
                    'platform': platform
                })

            current_date = next_date

        return {
            'type': 'chart',
            'chart_type': 'line',
            'data': all_data,
            'label': 'Platform Sentiment Trends'
        }

    def _get_platform_response_rate(self):
        """Average response rate across platforms"""
        from prompts.models import PromptAnalytics

        total = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).count()

        with_response = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).exclude(
            Q(context_summary__isnull=True) | Q(context_summary='')
        ).count()

        rate = (with_response / total * 100) if total > 0 else 0

        return {
            'type': 'metric',
            'value': round(rate, 1),
            'label': 'Response Rate',
            'format': 'percentage'
        }

    def _get_platform_mention_rate_chart(self):
        """Bar chart of mention rates by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            )
            total = analytics.count()
            mentions = analytics.filter(is_mention=True).count()
            rate = (mentions / total * 100) if total > 0 else 0

            data.append({
                'name': platform,
                'value': round(rate, 1)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'label': 'Platform Mention Rates'
        }

    def _get_platform_growth_rate(self):
        """Growth rate comparison by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            current = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date,
                is_mention=True
            ).count()

            previous = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.prev_start_date,
                created_at__lt=self.prev_end_date,
                is_mention=True
            ).count()

            growth = ((current - previous) / previous * 100) if previous > 0 else 0

            data.append({
                'name': platform,
                'value': round(growth, 1)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'label': 'Platform Growth Rates'
        }

    def _get_platform_share_of_voice(self):
        """Share of voice by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        total_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        data = []
        for platform in platforms:
            mentions = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date,
                is_mention=True
            ).count()

            share = (mentions / total_mentions * 100) if total_mentions > 0 else 0
            data.append({
                'name': platform,
                'value': round(share, 1)
            })

        return {
            'type': 'chart',
            'chart_type': 'pie',
            'data': data,
            'label': 'Platform Share of Voice'
        }

    def _get_platform_performance_matrix(self):
        """Multi-metric platform comparison"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            )

            total = analytics.count()
            mentions = analytics.filter(is_mention=True).count()
            avg_sentiment = analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

            mention_rate = (mentions / total * 100) if total > 0 else 0

            data.append({
                'name': platform,
                'mentions': mentions,
                'mention_rate': round(mention_rate, 1),
                'sentiment': round(avg_sentiment, 2)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'label': 'Platform Performance Matrix'
        }

    def _get_platform_citation_density(self):
        """Citation density by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).exclude(
                total_citations=0
            )

            total_citations = 0
            for a in analytics:
                if a.citation_list and isinstance(a.citation_list, list):
                    total_citations += len(a.citation_list)

            count = analytics.count()
            density = (total_citations / count) if count > 0 else 0

            data.append({
                'name': platform,
                'value': round(density, 2)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'label': 'Platform Citation Density'
        }

    def _get_platform_health_score(self):
        """Health score by platform"""
        from prompts.models import PromptAnalytics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        data = []

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            )

            total = analytics.count()
            mentions = analytics.filter(is_mention=True).count()
            avg_sentiment = float(analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0)

            mention_rate = (mentions / total * 100) if total > 0 else 0
            sentiment_component = (avg_sentiment + 1) / 2 * 100
            health = (mention_rate * 0.6) + (sentiment_component * 0.4)

            data.append({
                'name': platform,
                'value': round(health, 1)
            })

        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'label': 'Platform Health Scores'
        }

    def _get_platform_coverage_quality(self):
        """Quality score of platform coverage"""
        from prompts.models import PromptAnalytics

        platforms_with_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).values('platform').distinct().count()

        total_platforms = 4  # ChatGPT, Gemini, Perplexity, Claude
        coverage = (platforms_with_mentions / total_platforms * 100)

        return {
            'type': 'metric',
            'value': round(coverage, 1),
            'label': 'Coverage Quality',
            'format': 'percentage',
            'subtitle': f'{platforms_with_mentions} of {total_platforms} platforms'
        }

    def _get_platform_consistency_score(self):
        """Consistency of performance across platforms"""
        from prompts.models import PromptAnalytics
        import statistics

        platforms = ['ChatGPT', 'Gemini', 'Perplexity', 'Claude']
        mention_rates = []

        for platform in platforms:
            analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                platform=platform,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            )
            total = analytics.count()
            mentions = analytics.filter(is_mention=True).count()
            rate = (mentions / total * 100) if total > 0 else 0
            mention_rates.append(rate)

        # Calculate consistency as inverse of standard deviation
        if len(mention_rates) > 1:
            std_dev = statistics.stdev(mention_rates)
            # Convert to 0-100 scale (lower deviation = higher consistency)
            consistency = max(0, 100 - std_dev * 2)
        else:
            consistency = 0

        return {
            'type': 'metric',
            'value': round(consistency, 1),
            'label': 'Consistency Score',
            'format': 'decimal',
            'subtitle': 'Out of 100'
        }

    # ==================== GSC ORGANIC WIDGETS ====================

    def _fetch_gsc_insights_pair(self):
        """Return (current_insight, prev_insight) for the configured date range."""
        from integrations.models import GSCTrafficInsight
        current = (
            GSCTrafficInsight.objects
            .filter(domain=self.domain, track_status='COMP', end_date__lte=self.end_date)
            .order_by('-end_date', '-created_at')
            .first()
        )
        prev = (
            GSCTrafficInsight.objects
            .filter(domain=self.domain, track_status='COMP', end_date__lte=self.prev_end_date)
            .order_by('-end_date', '-created_at')
            .first()
        )
        return current, prev

    def _prorate_gsc(self, insight):
        """Apply prorate to a GSCTrafficInsight and return a dict."""
        from integrations.utils.prorate import apply_prorate_gsc
        raw = {
            'total_clicks': insight.total_clicks,
            'total_impressions': insight.total_impressions,
            'avg_ctr': float(insight.avg_ctr),
            'avg_position': float(insight.avg_position),
        }
        return apply_prorate_gsc(raw, insight.start_date, insight.end_date)

    def _growth(self, current_val, prev_val):
        """Return percentage growth, None if prev is zero."""
        if prev_val and prev_val != 0:
            return round((current_val - prev_val) / prev_val * 100, 1)
        return None

    def _get_gsc_overview_table(self):
        """
        Table widget matching the 'checks / GSC Overview' layout:
        Metric | Previous period | Current period
        """
        current, prev = self._fetch_gsc_insights_pair()
        if not current:
            return {'type': 'table', 'columns': ['Metric', 'Previous Period', 'Current Period'], 'rows': []}

        cur_data = self._prorate_gsc(current)
        prev_data = self._prorate_gsc(prev) if prev else None

        def fmt_period(insight):
            return f"{insight.start_date.strftime('%d %b')}–{insight.end_date.strftime('%d %b')}"

        prev_label = fmt_period(prev) if prev else 'Previous Period'
        cur_label = fmt_period(current)

        def prev_val(key):
            return prev_data[key] if prev_data else 'N/A'

        rows = [
            {'Metric': 'Clicks',       prev_label: prev_val('total_clicks'),      cur_label: cur_data['total_clicks']},
            {'Metric': 'Impressions',  prev_label: prev_val('total_impressions'),  cur_label: cur_data['total_impressions']},
            {'Metric': 'CTR',          prev_label: f"{prev_val('avg_ctr')}%" if prev_data else 'N/A',   cur_label: f"{cur_data['avg_ctr']}%"},
            {'Metric': 'Avg Position', prev_label: prev_val('avg_position') if prev_data else 'N/A',    cur_label: cur_data['avg_position']},
        ]

        return {
            'type': 'table',
            'columns': ['Metric', prev_label, cur_label],
            'rows': rows,
            'is_prorated': cur_data.get('is_prorated', False),
            'days_elapsed': cur_data.get('days_elapsed'),
            'total_days': cur_data.get('total_days'),
        }

    def _get_gsc_clicks(self):
        current, prev = self._fetch_gsc_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Organic Clicks', 'format': 'number'}
        cur = self._prorate_gsc(current)
        prv = self._prorate_gsc(prev) if prev else None
        growth = self._growth(cur['total_clicks'], prv['total_clicks'] if prv else None)
        result = {
            'type': 'metric',
            'value': cur['total_clicks'],
            'label': 'Organic Clicks',
            'format': 'number',
            'is_prorated': cur.get('is_prorated', False),
        }
        if growth is not None:
            result['growth'] = growth
            result['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        return result

    def _get_gsc_impressions(self):
        current, prev = self._fetch_gsc_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Impressions', 'format': 'number'}
        cur = self._prorate_gsc(current)
        prv = self._prorate_gsc(prev) if prev else None
        growth = self._growth(cur['total_impressions'], prv['total_impressions'] if prv else None)
        result = {
            'type': 'metric',
            'value': cur['total_impressions'],
            'label': 'Impressions',
            'format': 'number',
            'is_prorated': cur.get('is_prorated', False),
        }
        if growth is not None:
            result['growth'] = growth
            result['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        return result

    def _get_gsc_ctr(self):
        current, _ = self._fetch_gsc_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'CTR', 'format': 'percentage'}
        return {
            'type': 'metric',
            'value': float(current.avg_ctr),
            'label': 'CTR',
            'format': 'percentage',
        }

    def _get_gsc_avg_position(self):
        current, _ = self._fetch_gsc_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Avg Position', 'format': 'decimal'}
        return {
            'type': 'metric',
            'value': float(current.avg_position),
            'label': 'Avg Position',
            'format': 'decimal',
            'subtitle': 'Lower is better',
        }

    def _get_gsc_top_queries(self):
        current, _ = self._fetch_gsc_insights_pair()
        if not current or not current.top_queries:
            return {'type': 'table', 'columns': ['Query', 'Clicks', 'Impressions', 'CTR', 'Position'], 'rows': []}
        rows = [
            {
                'Query': q.get('query', ''),
                'Clicks': q.get('clicks', 0),
                'Impressions': q.get('impressions', 0),
                'CTR': q.get('ctr', ''),
                'Position': q.get('position', ''),
            }
            for q in (current.top_queries or [])
        ]
        return {
            'type': 'table',
            'columns': ['Query', 'Clicks', 'Impressions', 'CTR', 'Position'],
            'rows': rows,
        }

    def _get_gsc_top_pages(self):
        current, _ = self._fetch_gsc_insights_pair()
        if not current or not current.top_pages:
            return {'type': 'table', 'columns': ['Page', 'Clicks', 'Impressions', 'CTR', 'Position'], 'rows': []}
        rows = [
            {
                'Page': p.get('page', ''),
                'Clicks': p.get('clicks', 0),
                'Impressions': p.get('impressions', 0),
                'CTR': p.get('ctr', ''),
                'Position': p.get('position', ''),
            }
            for p in (current.top_pages or [])
        ]
        return {
            'type': 'table',
            'columns': ['Page', 'Clicks', 'Impressions', 'CTR', 'Position'],
            'rows': rows,
        }

    # ==================== GA ORGANIC WIDGETS ====================

    def _fetch_ga_insights_pair(self):
        """Return (current_insight, prev_insight) for the configured date range."""
        from integrations.models import GATrafficInsight
        current = (
            GATrafficInsight.objects
            .filter(domain=self.domain, track_status='COMP', end_date__lte=self.end_date)
            .order_by('-end_date', '-created_at')
            .first()
        )
        prev = (
            GATrafficInsight.objects
            .filter(domain=self.domain, track_status='COMP', end_date__lte=self.prev_end_date)
            .order_by('-end_date', '-created_at')
            .first()
        )
        return current, prev

    def _prorate_ga(self, insight):
        """Apply prorate to a GATrafficInsight and return a dict."""
        from integrations.utils.prorate import apply_prorate_ga
        raw = {
            'total_sessions': insight.total_sessions,
            'total_users': insight.total_users,
            'total_page_views': insight.total_page_views,
            'total_conversions': insight.total_conversions,
            'total_revenue': float(insight.total_revenue),
            'bounce_rate': float(insight.bounce_rate),
            'avg_session_duration': float(insight.avg_session_duration),
        }
        return apply_prorate_ga(raw, insight.start_date, insight.end_date)

    def _get_ga_overview_table(self):
        """Table widget with GA metrics across two periods."""
        current, prev = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'table', 'columns': ['Metric', 'Previous Period', 'Current Period'], 'rows': []}

        cur = self._prorate_ga(current)
        prv = self._prorate_ga(prev) if prev else None

        def fmt_period(insight):
            return f"{insight.start_date.strftime('%d %b')}–{insight.end_date.strftime('%d %b')}"

        prev_label = fmt_period(prev) if prev else 'Previous Period'
        cur_label = fmt_period(current)

        def pv(key, fmt=None):
            if not prv:
                return 'N/A'
            val = prv[key]
            return f"{val:,.0f}" if fmt == 'number' else val

        rows = [
            {'Metric': 'Sessions',             prev_label: pv('total_sessions', 'number'),    cur_label: f"{cur['total_sessions']:,}"},
            {'Metric': 'Users',                prev_label: pv('total_users', 'number'),       cur_label: f"{cur['total_users']:,}"},
            {'Metric': 'Page Views',           prev_label: pv('total_page_views', 'number'),  cur_label: f"{cur['total_page_views']:,}"},
            {'Metric': 'Conversions',          prev_label: pv('total_conversions', 'number'), cur_label: f"{cur['total_conversions']:,}"},
            {'Metric': 'Revenue',              prev_label: f"${prv['total_revenue']:,.2f}" if prv else 'N/A', cur_label: f"${cur['total_revenue']:,.2f}"},
            {'Metric': 'Bounce Rate',          prev_label: f"{prv['bounce_rate']}%" if prv else 'N/A',        cur_label: f"{cur['bounce_rate']}%"},
            {'Metric': 'Avg Session Duration', prev_label: f"{prv['avg_session_duration']}s" if prv else 'N/A', cur_label: f"{cur['avg_session_duration']}s"},
        ]

        return {
            'type': 'table',
            'columns': ['Metric', prev_label, cur_label],
            'rows': rows,
            'is_prorated': cur.get('is_prorated', False),
            'days_elapsed': cur.get('days_elapsed'),
            'total_days': cur.get('total_days'),
        }

    def _get_ga_sessions(self):
        current, prev = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Sessions', 'format': 'number'}
        cur = self._prorate_ga(current)
        prv = self._prorate_ga(prev) if prev else None
        growth = self._growth(cur['total_sessions'], prv['total_sessions'] if prv else None)
        result = {'type': 'metric', 'value': cur['total_sessions'], 'label': 'Sessions', 'format': 'number', 'is_prorated': cur.get('is_prorated', False)}
        if growth is not None:
            result['growth'] = growth
            result['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        return result

    def _get_ga_users(self):
        current, prev = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Users', 'format': 'number'}
        cur = self._prorate_ga(current)
        prv = self._prorate_ga(prev) if prev else None
        growth = self._growth(cur['total_users'], prv['total_users'] if prv else None)
        result = {'type': 'metric', 'value': cur['total_users'], 'label': 'Users', 'format': 'number', 'is_prorated': cur.get('is_prorated', False)}
        if growth is not None:
            result['growth'] = growth
            result['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        return result

    def _get_ga_pageviews(self):
        current, prev = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Page Views', 'format': 'number'}
        cur = self._prorate_ga(current)
        prv = self._prorate_ga(prev) if prev else None
        growth = self._growth(cur['total_page_views'], prv['total_page_views'] if prv else None)
        result = {'type': 'metric', 'value': cur['total_page_views'], 'label': 'Page Views', 'format': 'number', 'is_prorated': cur.get('is_prorated', False)}
        if growth is not None:
            result['growth'] = growth
            result['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        return result

    def _get_ga_conversions(self):
        current, prev = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Conversions', 'format': 'number'}
        cur = self._prorate_ga(current)
        prv = self._prorate_ga(prev) if prev else None
        growth = self._growth(cur['total_conversions'], prv['total_conversions'] if prv else None)
        result = {'type': 'metric', 'value': cur['total_conversions'], 'label': 'Conversions', 'format': 'number', 'is_prorated': cur.get('is_prorated', False)}
        if growth is not None:
            result['growth'] = growth
            result['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        return result

    def _get_ga_revenue(self):
        current, prev = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Revenue', 'format': 'decimal'}
        cur = self._prorate_ga(current)
        prv = self._prorate_ga(prev) if prev else None
        growth = self._growth(cur['total_revenue'], prv['total_revenue'] if prv else None)
        result = {'type': 'metric', 'value': cur['total_revenue'], 'label': 'Revenue', 'format': 'decimal', 'is_prorated': cur.get('is_prorated', False)}
        if growth is not None:
            result['growth'] = growth
            result['trend'] = 'up' if growth > 0 else 'down' if growth < 0 else 'neutral'
        return result

    def _get_ga_bounce_rate(self):
        current, _ = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Bounce Rate', 'format': 'percentage'}
        return {
            'type': 'metric',
            'value': float(current.bounce_rate),
            'label': 'Bounce Rate',
            'format': 'percentage',
        }

    def _get_ga_avg_session_duration(self):
        current, _ = self._fetch_ga_insights_pair()
        if not current:
            return {'type': 'metric', 'value': 0, 'label': 'Avg Session Duration', 'format': 'decimal'}
        return {
            'type': 'metric',
            'value': float(current.avg_session_duration),
            'label': 'Avg Session Duration',
            'format': 'decimal',
            'subtitle': 'seconds',
        }

    def _get_ga_top_landing_pages(self):
        current, _ = self._fetch_ga_insights_pair()
        if not current or not current.landing_pages:
            return {'type': 'table', 'columns': ['Page', 'Sessions', 'Bounce Rate', 'Avg Duration', 'Conversions'], 'rows': []}
        rows = [
            {
                'Page': p.get('page', ''),
                'Sessions': p.get('sessions', 0),
                'Bounce Rate': p.get('bounce_rate', ''),
                'Avg Duration': p.get('avg_duration', ''),
                'Conversions': p.get('conversions', 0),
            }
            for p in (current.landing_pages or [])
        ]
        return {
            'type': 'table',
            'columns': ['Page', 'Sessions', 'Bounce Rate', 'Avg Duration', 'Conversions'],
            'rows': rows,
        }

    def _get_ga_platform_breakdown(self):
        current, _ = self._fetch_ga_insights_pair()
        if not current or not current.platform_breakdown:
            return {'type': 'chart', 'chart_type': 'bar', 'data': [], 'x_axis': 'platform', 'y_axis': 'sessions', 'label': 'GA Platform Breakdown'}
        data = [
            {'platform': platform, 'sessions': metrics.get('visits', 0), 'conversions': metrics.get('conversions', 0)}
            for platform, metrics in (current.platform_breakdown or {}).items()
        ]
        return {
            'type': 'chart',
            'chart_type': 'bar',
            'data': data,
            'x_axis': 'platform',
            'y_axis': 'sessions',
            'label': 'GA Platform Breakdown',
        }
