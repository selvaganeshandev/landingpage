"""
Report Generation Service
Handles fetching data and coordinating report generation across different formats
"""
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q
from django.utils import timezone


class ReportDataService:
    """
    Service to fetch and aggregate data for reports
    """

    def __init__(self, domain, start_date, end_date, organisation):
        self.domain = domain
        self.start_date = start_date
        self.end_date = end_date
        self.organisation = organisation

    def get_executive_summary_data(self):
        """Fetch data for Executive Dashboard report"""
        from prompts.models import PromptAnalytics, Prompt
        from competitors.models import Competitor
        from analytics.models import SentimentAnalytics

        # Get prompt analytics in date range
        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        # Calculate key metrics
        total_prompts = Prompt.objects.filter(group__domain=self.domain).count()
        total_mentions = analytics.filter(is_mention=True).count()
        avg_sentiment = analytics.aggregate(
            avg_sentiment=Avg('sentiment_score')
        )['avg_sentiment'] or 0

        # Get competitor count
        competitor_count = Competitor.objects.filter(
            domain=self.domain
        ).count()

        # Get mention rate
        if total_prompts > 0:
            mention_rate = (total_mentions / (total_prompts * analytics.values('platform').distinct().count() or 1)) * 100
        else:
            mention_rate = 0

        # Get top performing prompts
        top_prompts = Prompt.objects.filter(
            group__domain=self.domain
        ).annotate(
            mention_count=Count('analytics', filter=Q(analytics__is_mention=True))
        ).order_by('-mention_count')[:5]

        # Get platform breakdown
        platform_breakdown = analytics.values('platform').annotate(
            count=Count('id'),
            mentions=Count('id', filter=Q(is_mention=True)),
            avg_sentiment=Avg('sentiment_score')
        ).order_by('-mentions')

        platform_data = [
            {
                'platform': p['platform'] or 'Unknown',
                'total': p['count'],
                'mentions': p['mentions'],
                'mention_rate': round((p['mentions'] / p['count'] * 100) if p['count'] > 0 else 0, 1),
                'avg_sentiment': round(p['avg_sentiment'] or 0, 2)
            }
            for p in platform_breakdown
        ]

        # Calculate sentiment breakdown
        positive_count = analytics.filter(sentiment_score__gt=0.3).count()
        neutral_count = analytics.filter(sentiment_score__gte=0, sentiment_score__lte=0.3).count()
        negative_count = analytics.filter(sentiment_score__lt=0).count()
        total_analyzed = positive_count + neutral_count + negative_count

        return {
            'period': {
                'start': self.start_date,
                'end': self.end_date,
            },
            'key_metrics': {
                'total_prompts': total_prompts,
                'total_mentions': total_mentions,
                'mention_rate': round(mention_rate, 1),
                'avg_sentiment': round(avg_sentiment, 2),
                'competitor_count': competitor_count,
            },
            'top_prompts': [
                {
                    'text': p.prompt[:100],
                    'mentions': p.mention_count,
                    'type': p.type,
                }
                for p in top_prompts
            ],
            'platform_breakdown': platform_data,
            'sentiment_breakdown': {
                'positive': positive_count,
                'neutral': neutral_count,
                'negative': negative_count,
                'total': total_analyzed,
                'positive_pct': round((positive_count / total_analyzed * 100) if total_analyzed > 0 else 0, 1),
                'neutral_pct': round((neutral_count / total_analyzed * 100) if total_analyzed > 0 else 0, 1),
                'negative_pct': round((negative_count / total_analyzed * 100) if total_analyzed > 0 else 0, 1),
            },
            'domain_name': self.domain.name,
            'domain_url': self.domain.url,
            'organisation_name': self.organisation.name,
        }

    def get_detailed_analytics_data(self):
        """Fetch data for Detailed Analytics report"""
        from prompts.models import PromptAnalytics, Prompt

        # Get all analytics
        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        # Group by LLM model
        llm_performance = {}
        for llm in ['chatgpt', 'claude', 'gemini', 'perplexity']:
            llm_analytics = analytics.filter(platform=llm)
            llm_performance[llm] = {
                'total': llm_analytics.count(),
                'mentions': llm_analytics.filter(is_mention=True).count(),
                'avg_sentiment': llm_analytics.aggregate(
                    avg=Avg('sentiment_score')
                )['avg'] or 0,
            }

        # Get prompt performance over time
        daily_stats = []
        current_date = self.start_date
        while current_date <= self.end_date:
            next_date = current_date + timedelta(days=1)
            day_analytics = analytics.filter(
                created_at__gte=current_date,
                created_at__lt=next_date
            )

            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'mentions': day_analytics.filter(is_mention=True).count(),
                'total': day_analytics.count(),
            })

            current_date = next_date

        return {
            'period': {
                'start': self.start_date,
                'end': self.end_date,
            },
            'llm_performance': llm_performance,
            'daily_stats': daily_stats,
            'domain_name': self.domain.name,
        }

    def get_competitor_focus_data(self):
        """Fetch data for Competitor Focus report"""
        from competitors.models import Competitor, CompetitorAnalytics, CompetitorPromptAnalytics
        from prompts.models import PromptAnalytics
        from django.db.models import Sum, Avg, Count

        # Get all competitors for this domain
        competitors = Competitor.objects.filter(domain=self.domain).order_by('-share_of_voice_percentage')

        # Calculate our brand metrics
        our_analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        our_mentions = our_analytics.filter(is_mention=True).count()
        our_total_prompts = our_analytics.values('prompt').distinct().count()
        our_avg_sentiment = our_analytics.aggregate(avg=Avg('sentiment_score'))['avg'] or 0
        our_visibility = (our_mentions / our_total_prompts * 100) if our_total_prompts > 0 else 0

        # Get competitor data with real metrics
        competitor_data = []
        total_market_mentions = our_mentions

        for competitor in competitors:
            # Get competitor analytics for the period
            # Filter by prompt creation date, not tracked_at (which is sync time)
            comp_analytics = CompetitorPromptAnalytics.objects.filter(
                competitor=competitor,
                prompt__created_at__gte=self.start_date,
                prompt__created_at__lte=self.end_date
            )

            # Use stored competitor metrics (updated from processing)
            mentions = competitor.total_mentions
            visibility = float(competitor.visibility_score)
            sentiment = float(competitor.sentiment_score)
            share_of_voice = float(competitor.share_of_voice_percentage)
            avg_position = float(competitor.average_position)
            trend = float(competitor.trend_percentage)

            # If no stored data, calculate from analytics
            if mentions == 0:
                mentions = comp_analytics.filter(is_mentioned=True).count()
                if mentions > 0:
                    sentiment = float(comp_analytics.aggregate(avg=Avg('sentiment_score'))['avg'] or 0)

            total_market_mentions += mentions

            competitor_data.append({
                'name': competitor.name,
                'url': competitor.url,
                'mentions': mentions,
                'visibility_score': round(visibility, 1),
                'sentiment_score': round(sentiment, 2),
                'share_of_voice': round(share_of_voice, 1),
                'average_position': round(avg_position, 1),
                'trend': round(trend, 1),
                'status': competitor.track_status,
            })

        # Calculate share of voice for our brand
        our_share_of_voice = (our_mentions / total_market_mentions * 100) if total_market_mentions > 0 else 0

        # Sort by mentions (highest first)
        competitor_data.sort(key=lambda x: x['mentions'], reverse=True)

        # Get platform breakdown for our brand
        platform_breakdown = our_analytics.values('platform').annotate(
            count=Count('id'),
            mentions=Count('id', filter=Q(is_mention=True))
        ).order_by('-mentions')

        platform_data = [
            {
                'platform': p['platform'] or 'Unknown',
                'total': p['count'],
                'mentions': p['mentions'],
                'mention_rate': round((p['mentions'] / p['count'] * 100) if p['count'] > 0 else 0, 1)
            }
            for p in platform_breakdown
        ]

        return {
            'period': {
                'start': self.start_date,
                'end': self.end_date,
            },
            'domain_name': self.domain.name,
            'domain_url': self.domain.url,
            'our_metrics': {
                'mentions': our_mentions,
                'visibility_score': round(our_visibility, 1),
                'sentiment_score': round(our_avg_sentiment, 2),
                'share_of_voice': round(our_share_of_voice, 1),
                'total_prompts': our_total_prompts,
            },
            'competitors': competitor_data,
            'total_competitors': len(competitor_data),
            'total_market_mentions': total_market_mentions,
            'platform_breakdown': platform_data,
        }

    def get_content_strategy_data(self):
        """Fetch data for Content Strategy report"""
        from prompts.models import Prompt, PromptAnalytics, PromptGroup
        from topics.models import Topic
        from keywords.models import Keyword
        from competitors.models import Competitor
        from django.db.models import Count, Avg, Sum, Q

        # Get all prompts and analytics
        all_prompts = Prompt.objects.filter(group__domain=self.domain)
        analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )

        # Calculate overview metrics
        total_prompts = all_prompts.count()
        total_mentions = analytics.filter(is_mention=True).count()
        total_citations = analytics.aggregate(Sum('total_citations'))['total_citations__sum'] or 0
        avg_sentiment = analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0
        avg_engagement = analytics.aggregate(Avg('engagement_score'))['engagement_score__avg'] or 0

        # Previous period for comparison
        period_length = (self.end_date - self.start_date).days
        prev_start = self.start_date - timedelta(days=period_length)
        prev_end = self.start_date

        prev_analytics = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=prev_start,
            created_at__lte=prev_end
        )
        prev_mentions = prev_analytics.filter(is_mention=True).count()
        mentions_growth = ((total_mentions - prev_mentions) / prev_mentions * 100) if prev_mentions > 0 else 0

        # Get ALL topics with analytics
        topics = Topic.objects.filter(domain=self.domain).order_by('-total_mentions')
        topic_performance = []
        for topic in topics:  # Get ALL topics, not just top 10
            coverage_score = min(topic.total_mentions / 10, 100) if topic.total_mentions > 0 else 0

            topic_performance.append({
                'name': topic.name,
                'keywords': topic.keyword_list[:5] if topic.keyword_list else [],
                'coverage_score': round(coverage_score, 0),
                'mentions': topic.total_mentions,
                'engagement': round(avg_engagement, 0),
                'growth': round(topic.trend_percentage, 0),
                'sentiment': round(topic.sentiment_score, 2),
            })

        # Identify content gaps (keywords/topics with no or low coverage)
        all_keywords = Keyword.objects.filter(domain=self.domain)
        content_gaps = []
        for keyword in all_keywords:
            # Find prompts related to this keyword
            related_prompts = all_prompts.filter(prompt__icontains=keyword.keyword)
            mention_count = analytics.filter(
                prompt__in=related_prompts,
                is_mention=True
            ).count()

            if mention_count == 0:
                # Estimate search volume and opportunity (mock data for now)
                content_gaps.append({
                    'keyword': keyword.keyword,
                    'search_volume': keyword.priority * 1000,  # Mock calculation
                    'competitor_coverage': 0,  # Can be enhanced with competitor data
                    'opportunity_score': keyword.priority * 10,
                    'estimated_traffic': keyword.priority * 100,
                    'priority': 'Critical' if keyword.priority >= 8 else ('High' if keyword.priority >= 5 else 'Medium'),
                })

        # Sort gaps by opportunity score - Include ALL gaps
        content_gaps = sorted(content_gaps, key=lambda x: x['opportunity_score'], reverse=True)

        # Get untapped keywords (keywords with zero mentions)
        untapped_keywords = []
        for keyword in all_keywords[:20]:
            related_analytics = analytics.filter(prompt__prompt__icontains=keyword.keyword)
            if not related_analytics.filter(is_mention=True).exists():
                untapped_keywords.append({
                    'keyword': keyword.keyword,
                    'mentions': 0,
                    'priority': 'High' if keyword.priority >= 5 else 'Medium',
                    'search_volume': keyword.priority * 1000,
                })

        # Get trending keywords (with growing mentions)
        trending_keywords = []
        for keyword in all_keywords[:20]:
            related_analytics = analytics.filter(prompt__prompt__icontains=keyword.keyword)
            current_mentions = related_analytics.filter(is_mention=True).count()

            prev_related = prev_analytics.filter(prompt__prompt__icontains=keyword.keyword)
            prev_keyword_mentions = prev_related.filter(is_mention=True).count()

            if prev_keyword_mentions > 0 and current_mentions > prev_keyword_mentions:
                growth = ((current_mentions - prev_keyword_mentions) / prev_keyword_mentions) * 100
                trending_keywords.append({
                    'keyword': keyword.keyword,
                    'mentions': current_mentions,
                    'growth': round(growth, 0),
                    'search_volume': keyword.priority * 1000,
                })

        trending_keywords = sorted(trending_keywords, key=lambda x: x['growth'], reverse=True)[:10]

        # Get competitor comparison data
        competitors = Competitor.objects.filter(domain=self.domain)[:5]
        competitor_comparison = []
        for comp in competitors:
            competitor_comparison.append({
                'name': comp.name,
                'url': comp.url,
            })

        # Get Answer Gap data (prompts where competitors are mentioned but you're not)
        from competitors.models import CompetitorPromptAnalytics
        from django.db.models import Q

        # Get all unique prompts for this domain that have competitor mentions
        prompts_with_competitor_mentions = set(
            CompetitorPromptAnalytics.objects.filter(
                competitor__domain_id=self.domain.id,
                is_mentioned=True,
                prompt__created_at__gte=self.start_date,
                prompt__created_at__lte=self.end_date
            ).values_list('prompt_id', flat=True)
        )

        # For each unique prompt, check if YOUR brand is mentioned
        answer_gaps = []
        for prompt_id in prompts_with_competitor_mentions:
            # Check if your brand is mentioned in this prompt
            your_mention = analytics.filter(
                prompt_id=prompt_id,
                is_mention=True
            ).exists()

            if not your_mention:
                # This is a gap! Competitors mentioned but you're not
                try:
                    prompt = Prompt.objects.select_related('group__domain').get(id=prompt_id)
                except Prompt.DoesNotExist:
                    continue

                # Get unique competitors and their data
                competitor_map = {}
                platforms_set = set()

                for ca in CompetitorPromptAnalytics.objects.filter(
                    prompt_id=prompt_id,
                    is_mentioned=True
                ).select_related('competitor'):
                    comp_name = ca.competitor.name
                    platforms_set.add(ca.platform)

                    if comp_name not in competitor_map:
                        competitor_map[comp_name] = {
                            'name': comp_name,
                            'mentions': ca.mention_count,
                            'position': ca.position
                        }

                competitors_list = list(competitor_map.values())
                platforms = list(platforms_set)

                answer_gaps.append({
                    'prompt_id': prompt.id,
                    'prompt_text': prompt.prompt,
                    'competitors': competitors_list,
                    'platforms': platforms,
                    'total_competitor_mentions': len(competitors_list),
                    'your_mentions': 0
                })

        # Sort by total competitor mentions (highest opportunity first)
        answer_gaps.sort(key=lambda x: x['total_competitor_mentions'], reverse=True)

        return {
            'period': {
                'start': self.start_date,
                'end': self.end_date,
            },
            'domain_name': self.domain.name,
            'domain_url': self.domain.url,
            'overview': {
                'content_quality_score': round(avg_sentiment * 50 + 50, 0),  # Convert -1 to 1 range to 0-100
                'topics_covered': topics.count(),
                'topics_growth': round(mentions_growth / 4, 0),  # Approximate topic growth
                'content_gaps_found': len(content_gaps),
                'answer_gaps_found': len(answer_gaps),
                'engagement_rate': round(avg_engagement, 0),
                'engagement_growth': round(mentions_growth / 2, 0),  # Approximate
            },
            'content_gaps': content_gaps,  # All critical gaps
            'answer_gaps': answer_gaps,  # All answer gaps
            'topic_performance': topic_performance,
            'untapped_keywords': untapped_keywords[:10],
            'trending_keywords': trending_keywords[:5],
            'competitor_comparison': competitor_comparison,
            'recommendations': self._generate_recommendations(content_gaps, topic_performance, trending_keywords),
        }

    def _generate_recommendations(self, content_gaps, topic_performance, trending_keywords):
        """Generate strategic recommendations based on data"""
        recommendations = []

        # Recommendation 1: Address top content gap
        if content_gaps:
            top_gap = content_gaps[0]
            recommendations.append({
                'priority': 1,
                'title': f'Address {top_gap["keyword"]} Content Gap',
                'description': f'This is a critical gap with opportunity score {top_gap["opportunity_score"]}/100. Create comprehensive content to capture {top_gap["estimated_traffic"]} monthly traffic.',
                'timeline': '7 days',
                'content_pieces': '5-7 articles',
                'expected_traffic': f'+{top_gap["estimated_traffic"]}/mo',
            })

        # Recommendation 2: Focus on low-performing topics
        low_performers = [t for t in topic_performance if t['coverage_score'] < 60]
        if low_performers:
            recommendations.append({
                'priority': 2,
                'title': f'Improve {low_performers[0]["name"]} Coverage',
                'description': f'Current coverage is {low_performers[0]["coverage_score"]}%. Expand content to improve visibility and capture emerging audience.',
                'timeline': '14 days',
                'content_pieces': '4-6 articles',
                'expected_traffic': '+500/mo',
            })

        # Recommendation 3: Amplify top performers
        top_performers = [t for t in topic_performance if t['coverage_score'] >= 80]
        if top_performers:
            recommendations.append({
                'priority': 3,
                'title': f'Maintain {top_performers[0]["name"]} Excellence',
                'description': f'Strongest category ({top_performers[0]["coverage_score"]}% coverage, {top_performers[0]["mentions"]} mentions). Maintain dominance by refreshing content quarterly.',
                'timeline': 'Ongoing',
                'content_pieces': 'Quarterly refresh',
                'expected_traffic': 'Market Leader',
            })

        return recommendations
