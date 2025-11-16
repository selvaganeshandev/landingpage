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
            'domain_name': self.domain.name,
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
        from competitors.models import Competitor
        from prompts.models import PromptAnalytics

        # Get all competitors
        competitors = Competitor.objects.filter(domain=self.domain)

        competitor_data = []
        for competitor in competitors:
            # Get mention count for competitor
            mentions = PromptAnalytics.objects.filter(
                prompt__group__domain=self.domain,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date,
                response_text__icontains=competitor.name
            ).count()

            competitor_data.append({
                'name': competitor.name,
                'website': competitor.website,
                'mentions': mentions,
                'description': competitor.description or '',
            })

        # Sort by mentions
        competitor_data.sort(key=lambda x: x['mentions'], reverse=True)

        # Get our domain's mention count
        our_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            is_mention=True
        ).count()

        return {
            'period': {
                'start': self.start_date,
                'end': self.end_date,
            },
            'domain_name': self.domain.name,
            'our_mentions': our_mentions,
            'competitors': competitor_data,
        }

    def get_content_strategy_data(self):
        """Fetch data for Content Strategy report"""
        from prompts.models import Prompt, PromptAnalytics
        from topics.models import Topic

        # Get all prompts
        all_prompts = Prompt.objects.filter(group__domain=self.domain)

        # Get prompts with no mentions (content gaps)
        gap_prompts = []
        for prompt in all_prompts:
            mentions = PromptAnalytics.objects.filter(
                prompt=prompt,
                is_mention=True,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).count()

            if mentions == 0:
                gap_prompts.append({
                    'text': prompt.prompt[:100],
                    'type': prompt.type,
                })

        # Get topics
        topics = Topic.objects.filter(domain=self.domain)
        topic_data = [
            {
                'name': topic.name,
                'description': topic.description or '',
            }
            for topic in topics[:10]
        ]

        # Get optimization opportunities (low-performing prompts)
        low_performers = []
        for prompt in all_prompts:
            analytics = PromptAnalytics.objects.filter(
                prompt=prompt,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            )

            if analytics.exists():
                mention_rate = analytics.filter(is_mention=True).count() / analytics.count()
                if mention_rate < 0.3:  # Less than 30% mention rate
                    low_performers.append({
                        'text': prompt.prompt[:100],
                        'mention_rate': round(mention_rate * 100, 1),
                    })

        return {
            'period': {
                'start': self.start_date,
                'end': self.end_date,
            },
            'domain_name': self.domain.name,
            'content_gaps': gap_prompts[:20],  # Top 20 gaps
            'topics': topic_data,
            'optimization_opportunities': low_performers[:15],  # Top 15
        }
