"""
Competitor Extraction Service
Automatically extracts top competitors from prompt analytics data
"""
from decimal import Decimal
from django.db.models import Count, Q, Sum
from django.utils import timezone
from collections import Counter
import re
from typing import List, Dict, Tuple, Optional
from .models import Competitor
from prompts.models import PromptAnalytics
from domains.models import Domain
from analytics.models import ShareOfVoiceAnalytics


class CompetitorExtractionService:
    """
    Service to extract and create competitor records from prompt analytics data
    """
    POSITIVE_KEYWORDS = [
        'best', 'great', 'excellent', 'top', 'leading', 'premier',
        'quality', 'popular', 'trusted', 'recommended', 'fast', 'easy',
        'comprehensive', 'cost-effective', 'popular', 'reliable'
    ]
    NEGATIVE_KEYWORDS = [
        'poor', 'worst', 'bad', 'inferior', 'low-quality', 'slow',
        'difficult', 'expensive', 'limited', 'outdated', 'problem',
        'issue', 'buggy', 'unreliable'
    ]
    
    POSITIVE_KEYWORDS = [
        'best', 'great', 'excellent', 'top', 'leading', 'premier',
        'quality', 'popular', 'trusted', 'recommended', 'fast', 'easy'
    ]
    NEGATIVE_KEYWORDS = [
        'poor', 'worst', 'bad', 'inferior', 'low-quality', 'slow',
        'difficult', 'expensive', 'limited', 'outdated', 'problem'
    ]

    def __init__(self, domain: Domain):
        self.domain = domain
        self.min_competitors = 3
        self.max_competitors = 5
        self.min_mentions_threshold = 2  # Minimum mentions to be considered a competitor

    def extract_and_create_competitors(self) -> Tuple[int, List[str]]:
        """
        Extract top competitors from prompt analytics and create Competitor records

        Returns:
            Tuple of (created_count, list_of_competitor_names)
        """
        print(f"Starting competitor extraction for domain: {self.domain.name}")

        # Step 1: Get all prompt analytics for this domain
        analytics_qs = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain
        ).values('competitor_mention_list', 'context_summary', 'sentiment_score')
        total_prompts = analytics_qs.count()

        # Step 2: Extract and count all competitor mentions + sentiment estimates
        competitor_stats: Dict[str, Dict[str, float]] = {}

        for analytics in analytics_qs:
            mention_list = analytics.get('competitor_mention_list') or []
            context_summary = analytics.get('context_summary') or ''
            if mention_list and isinstance(mention_list, list):
                for competitor_name in mention_list:
                    if competitor_name and isinstance(competitor_name, str):
                        # Clean and normalize the competitor name
                        cleaned_name = self._clean_competitor_name(competitor_name)
                        if cleaned_name and cleaned_name.lower() != self.domain.name.lower():
                            stats = competitor_stats.setdefault(cleaned_name, {
                                'mentions': 0,
                                'sentiment_sum': 0.0,
                                'sentiment_samples': 0
                            })
                            stats['mentions'] += 1
                            sentiment_estimate = self._analyze_competitor_sentiment(
                                context_summary=context_summary,
                                competitor_name=cleaned_name
                            )
                            stats['sentiment_sum'] += sentiment_estimate
                            stats['sentiment_samples'] += 1

        competitor_counter = Counter({
            name: data['mentions']
            for name, data in competitor_stats.items()
        })

        print(f"Found {len(competitor_counter)} unique competitor mentions")

        # Step 3: Filter competitors by minimum threshold
        filtered_competitors = {
            name: count for name, count in competitor_counter.items()
            if count >= self.min_mentions_threshold
        }

        print(f"Filtered to {len(filtered_competitors)} competitors with >= {self.min_mentions_threshold} mentions")

        # Step 4: Get top N competitors (between min and max)
        sorted_competitors = sorted(
            competitor_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )
        # Start with competitors meeting the threshold
        top_competitors = [
            item for item in sorted_competitors
            if item[0] in filtered_competitors
        ][:self.max_competitors]
        
        # Ensure we always return up to max_competitors (or all available) by
        # backfilling with lower-frequency competitors when needed.
        target_count = min(self.max_competitors, len(sorted_competitors))
        if len(top_competitors) < target_count:
            existing = {name for name, _ in top_competitors}
            for name, count in sorted_competitors:
                if name in existing:
                    continue
                top_competitors.append((name, count))
                if len(top_competitors) == target_count:
                    break
        
        # Guarantee a minimum of min_competitors whenever we have enough data
        if len(top_competitors) < self.min_competitors:
            top_competitors = sorted_competitors[:self.min_competitors]

        print(f"Selected top {len(top_competitors)} competitors")

        # Step 5: Create Competitor records
        created_competitors = []
        competitor_entries: List[Tuple[Competitor, int]] = []
        created_count = 0

        for competitor_name, mention_count in top_competitors:
            # Try to extract/guess URL
            competitor_url = self._guess_competitor_url(competitor_name)
            stats = competitor_stats.get(competitor_name, {})
            avg_sentiment = self._calculate_average_sentiment(stats)
            sentiment_decimal = Decimal(str(round(avg_sentiment, 2)))

            # Create or update competitor
            competitor, created = Competitor.objects.get_or_create(
                domain=self.domain,
                name=competitor_name,
                defaults={
                    'url': competitor_url,
                    'total_mentions': mention_count,
                    'sentiment_score': sentiment_decimal,
                    'track_status': 'INIT',
                    'track_message': 'Auto-extracted from prompt analytics',
                    'tracked_at': timezone.now(),
                }
            )

            if created:
                created_count += 1
                created_competitors.append(competitor_name)
                print(f"Created competitor: {competitor_name} ({mention_count} mentions)")
            else:
                # Update mention count if competitor already exists
                fields_to_update = []
                if competitor.total_mentions != mention_count:
                    competitor.total_mentions = mention_count
                    fields_to_update.append('total_mentions')
                if competitor.sentiment_score != sentiment_decimal:
                    competitor.sentiment_score = sentiment_decimal
                    fields_to_update.append('sentiment_score')
                if fields_to_update:
                    competitor.save(update_fields=fields_to_update + ['modified_at'])
                    print(f"Updated competitor: {competitor_name} ({mention_count} mentions)")
            competitor_entries.append((competitor, mention_count))

        # Update share of voice percentages so frontend "Share" column isn't zero
        self._update_share_of_voice_estimates(competitor_entries, total_prompts)

        print(f"Competitor extraction complete. Created {created_count} new competitors.")
        self._set_zero_sentiment_for_unmentioned()
        return created_count, created_competitors

    def _clean_competitor_name(self, name: str) -> str:
        """
        Clean and normalize competitor name
        """
        if not name:
            return ""

        # Remove common suffixes and prefixes
        name = name.strip()

        # Remove URL protocols and www
        name = re.sub(r'^https?://(www\.)?', '', name, flags=re.IGNORECASE)

        # Remove trailing slashes and paths
        name = name.split('/')[0]

        # Remove common company suffixes for cleaner names
        suffixes = [
            r'\s+(Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?|Company|Co\.?)$',
            r'\.(com|net|org|io|ai)$'
        ]
        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)

        # Capitalize properly
        name = name.strip()

        # If it's all lowercase or all uppercase, title case it
        if name.islower() or name.isupper():
            name = name.title()

        return name

    def _guess_competitor_url(self, competitor_name: str) -> str:
        """
        Attempt to guess competitor URL from name
        """
        # Clean the name for URL
        clean_name = competitor_name.lower().strip()

        # Remove spaces and special characters
        clean_name = re.sub(r'[^a-z0-9]', '', clean_name)

        # Common patterns
        possible_urls = [
            f"https://www.{clean_name}.com",
            f"https://{clean_name}.com",
            f"https://www.{clean_name}.io",
            f"https://{clean_name}.io",
        ]

        # Return the most likely one (first .com)
        return possible_urls[0]

    def _calculate_average_sentiment(self, stats: Dict[str, float]) -> float:
        samples = stats.get('sentiment_samples', 0)
        if not samples:
            return 0.0
        return stats['sentiment_sum'] / samples

    def _analyze_competitor_sentiment(self, context_summary: str, competitor_name: str) -> float:
        """
        Reuse the same lightweight sentiment heuristic as the competitor processor.
        """
        if not context_summary:
            return 0.0

        response_lower = context_summary.lower()
        competitor_lower = competitor_name.lower()

        if competitor_lower not in response_lower:
            return 0.0

        # Focus on sentences mentioning the competitor
        sentences = re.split(r'(?<=[.!?])\s+', context_summary)
        relevant_sentences = [s for s in sentences if competitor_lower in s.lower()]
        relevant_text = ' '.join(relevant_sentences) if relevant_sentences else context_summary
        relevant_lower = relevant_text.lower()

        pos_hits = sum(relevant_lower.count(word) for word in self.POSITIVE_KEYWORDS)
        neg_hits = sum(relevant_lower.count(word) for word in self.NEGATIVE_KEYWORDS)

        if pos_hits == 0 and neg_hits == 0:
            return 0.0

        sentiment = 0.0
        if pos_hits > neg_hits:
            sentiment = 0.5
        elif neg_hits > pos_hits:
            sentiment = -0.5

        # Normalize to [-1, 1]
        return max(-1.0, min(1.0, sentiment))

    def _update_share_of_voice_estimates(self, competitor_entries: List[Tuple[Competitor, int]], total_prompts: int) -> None:
        """
        Estimate share of voice percentages immediately after extraction so the UI
        can display non-zero values even before full competitor processing runs.
        """
        if not competitor_entries:
            return
        if total_prompts <= 0:
            total_prompts = len(competitor_entries)  # fallback to number of competitors

        # Total competitor mentions (only the tracked competitors)
        competitor_total = sum(mention_count for _, mention_count in competitor_entries)

        # Your own brand mentions from prompt analytics (completed prompts only)
        own_mentions = PromptAnalytics.objects.filter(
            prompt__group__domain=self.domain,
            is_mention=True,
            track_status='COMP'
        ).aggregate(total=Sum('total_mentions'))['total'] or 0

        total_market_mentions = competitor_total + own_mentions
        if total_market_mentions == 0:
            return

        today = timezone.now().date()

        # Update competitors
        for competitor, mention_count in competitor_entries:
            share_pct = Decimal(str(round((mention_count / total_market_mentions) * 100, 2)))
            visibility_score = self._calculate_visibility_score(
                total_prompts=total_prompts,
                mentioned_count=mention_count,
                avg_position=None
            )

            updates = []
            if competitor.share_of_voice_percentage != share_pct:
                competitor.share_of_voice_percentage = share_pct
                updates.append('share_of_voice_percentage')
            if competitor.visibility_score != visibility_score:
                competitor.visibility_score = visibility_score
                updates.append('visibility_score')
            if updates:
                competitor.save(update_fields=updates + ['modified_at'])

            ShareOfVoiceAnalytics.objects.update_or_create(
                domain=self.domain,
                competitor=competitor,
                platform='ChatGPT',
                timestamp=today,
                defaults={
                    'share_percentage': share_pct,
                    'mention_count': mention_count,
                    'market_position': None,
                }
            )

        # Update your own brand record (competitor=None)
        own_share_pct = Decimal(str(round((own_mentions / total_market_mentions) * 100, 2)))
        ShareOfVoiceAnalytics.objects.update_or_create(
            domain=self.domain,
            competitor=None,
            platform='ChatGPT',
            timestamp=today,
            defaults={
                'share_percentage': own_share_pct,
                'mention_count': own_mentions,
                'market_position': None,
            }
        )

        # Refresh market positions (rankings)
        sov_records = ShareOfVoiceAnalytics.objects.filter(
            domain=self.domain,
            platform='ChatGPT',
            timestamp=today
        ).order_by('-share_percentage')

        for idx, sov in enumerate(sov_records, start=1):
            if sov.market_position != idx:
                sov.market_position = idx
                sov.save(update_fields=['market_position'])

    def _calculate_visibility_score(
        self,
        total_prompts: int,
        mentioned_count: int,
        avg_position: Optional[float] = None
    ) -> Decimal:
        """
        Match the competitor processor’s visibility formula so cards never show 0
        before the engine processes them.
        """
        if total_prompts <= 0:
            return Decimal('0.0')

        mention_rate = mentioned_count / total_prompts if total_prompts else 0
        position_weight = 1.0 / (avg_position if avg_position and avg_position > 0 else 1.0)
        score = min(mention_rate * position_weight * 100, 100)
        return Decimal(str(round(score, 2)))

    def _set_zero_sentiment_for_unmentioned(self) -> None:
        """
        Ensure competitors with zero mentions display 0% sentiment (represented
        as -1.0 in the -1 to 1 scoring we use throughout the app).
        """
        zero_competitors = Competitor.objects.filter(
            domain=self.domain,
            total_mentions__lte=0
        )
        for comp in zero_competitors:
            if comp.sentiment_score != Decimal('-1.0'):
                comp.sentiment_score = Decimal('-1.0')
                comp.save(update_fields=['sentiment_score', 'modified_at'])

    @classmethod
    def extract_for_domain(cls, domain_id: int) -> Tuple[int, List[str]]:
        """
        Class method to extract competitors for a domain by ID

        Args:
            domain_id: ID of the domain

        Returns:
            Tuple of (created_count, list_of_competitor_names)
        """
        try:
            domain = Domain.objects.get(id=domain_id)
            service = cls(domain)
            return service.extract_and_create_competitors()
        except Domain.DoesNotExist:
            print(f"Domain with ID {domain_id} does not exist")
            return 0, []
        except Exception as e:
            print(f"Error extracting competitors for domain {domain_id}: {str(e)}")
            return 0, []
