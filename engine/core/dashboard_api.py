from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q, Min, Max
from datetime import timedelta, datetime, date
from shared_models.models import (
    Domain, PromptAnalytics, ShareOfVoiceAnalytics, Competitor,
    DomainMetricSnapshot, PromptGroupMetricSnapshot
)

# Platform label on the aggregate ("one row per brand") share-of-voice rows.
# Defined next to the writer in competitor_processor; kept as a literal here so
# the read-only dashboard path does not import the processor (and its LLM
# client) just to read one constant. Must stay in sync with that module.
SOV_OVERALL_PLATFORM = 'Overall'


def calculate_relative_time(dt):
    """Calculate relative time string like '2 hours ago'"""
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def get_sentiment_category(sentiment_score):
    """Convert sentiment score to category"""
    if sentiment_score is None:
        return "neutral"
    score = float(sentiment_score)
    if score > 0.33:
        return "positive"
    elif score < -0.33:
        return "negative"
    else:
        return "neutral"


def format_date_for_chart(date_obj):
    """Format date for chart display (e.g., 'Oct 1', 'Nov 12')"""
    if isinstance(date_obj, str):
        date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return f"{month_names[date_obj.month - 1]} {date_obj.day}"


def get_period_type(days):
    """
    Determine the appropriate period type based on number of days.
    - daily: for periods < 30 days
    - weekly: for periods 30-90 days
    - monthly: for periods > 90 days
    """
    if days < 30:
        return 'daily'
    elif days <= 90:
        return 'weekly'
    else:
        return 'monthly'


def latest_day_total(snapshot_qs, field):
    """Sum `field` across platforms on the MOST RECENT snapshot date in `snapshot_qs`.

    Headline mentions/citations used to be Sum() over the whole window, which
    added every tracking run together: a domain swept four times in 30 days
    reported roughly four periods stacked (~19k where the latest run was ~5k),
    and the figure grew with how often tracking ran rather than with visibility.
    Snapshots are per (platform x date), so the current standing is the latest
    date summed across its platforms — which is also what the Share of Voice
    card reports, so the two screens finally agree.

    Returns 0 for an empty queryset.
    """
    latest = snapshot_qs.aggregate(d=Max('snapshot_date'))['d']
    if latest is None:
        return 0
    return snapshot_qs.filter(snapshot_date=latest).aggregate(
        total=Sum(field)
    )['total'] or 0


def get_period_types_for_query(days):
    """
    Get list of period_types to query based on requested days.
    Always includes more granular period_types as fallback.
    This ensures we can query daily snapshots when weekly/monthly don't exist.
    """
    if days < 30:
        return ['daily']  # Only daily needed
    elif days <= 90:
        return ['weekly', 'daily']  # Try weekly first, fallback to daily
    else:
        return ['monthly', 'weekly', 'daily']  # Try monthly, fallback to weekly/daily


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_summary(request):
    """
    Get comprehensive dashboard data for a domain, filtered by days.
    
    Query Parameters:
    - domain_id (required): Domain ID
    - days (optional, default=30): Number of days to look back (7, 30, 90, etc.)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    domain_id = request.query_params.get('domain_id')
    days = int(request.query_params.get('days', 30))
    
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get domain
    domain = get_object_or_404(Domain, id=domain_id)
    
    # Calculate date range
    # For "last N days", we want the last N days including today
    # If days=7 and today is Dec 15, we want Dec 9-15 (7 days: Dec 9, 10, 11, 12, 13, 14, 15)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)  # Subtract (days-1) to include today in the count
    
    # Debug: Log calculated dates
    logger.info(f"Dashboard API: Calculated date range for {days} days - start_date: {start_date}, end_date: {end_date}")
    
    # Calculate previous period for change comparison
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=days)
    
    # Determine period type based on days (for display/trends)
    period_type = get_period_type(days)
    
    # Get period types to query (with fallback to more granular types)
    period_types = get_period_types_for_query(days)
    
    # 1. Get metrics from DomainMetricSnapshot (time snapshot functionality)
    # Use metric snapshots for aggregated metrics - much faster than querying raw analytics
    # Query with fallback to more granular period_types
    # DomainMetricSnapshot records are platform-specific, so we aggregate across all platforms
    # Debug: Log the query parameters
    logger.info(f"Dashboard API: Querying snapshots for domain {domain_id}, date range: {start_date} to {end_date}, period_types: {period_types}")
    
    snapshot_qs = DomainMetricSnapshot.objects.filter(
        domain_id=domain_id,
        snapshot_date__gte=start_date,
        snapshot_date__lte=end_date,
        period_type__in=period_types
    ).exclude(platform__isnull=True).exclude(platform='')  # Only use platform-specific snapshots
    
    # Debug: Log snapshot count and check all snapshots for this domain
    snapshot_count_before_agg = snapshot_qs.count()
    logger.info(f"Dashboard API: Found {snapshot_count_before_agg} snapshots matching criteria")
    
    # Debug: Check all snapshots for this domain to see what dates exist
    all_snapshots = DomainMetricSnapshot.objects.filter(domain_id=domain_id).exclude(platform__isnull=True).exclude(platform='')
    all_snapshot_count = all_snapshots.count()
    logger.info(f"Dashboard API: Total snapshots for domain {domain_id}: {all_snapshot_count}")
    if all_snapshot_count > 0:
        # Get date range of all snapshots
        date_range = all_snapshots.aggregate(
            min_date=Min('snapshot_date'),
            max_date=Max('snapshot_date')
        )
        logger.info(f"Dashboard API: Snapshot date range: {date_range['min_date']} to {date_range['max_date']}")
        # Get sample snapshots with dates
        sample_snapshots = list(all_snapshots[:10].values('snapshot_date', 'platform', 'period_type', 'mentions', 'citations'))
        logger.info(f"Dashboard API: Sample all snapshots: {sample_snapshots}")
    
    if snapshot_count_before_agg > 0:
        sample_snapshots = list(snapshot_qs[:5].values('snapshot_date', 'platform', 'period_type', 'mentions'))
        logger.info(f"Dashboard API: Sample filtered snapshots: {sample_snapshots}")
    
    # Get previous period metrics for change calculation
    prev_snapshot_qs = DomainMetricSnapshot.objects.filter(
        domain_id=domain_id,
        snapshot_date__gte=prev_start_date,
        snapshot_date__lte=prev_end_date,
        period_type__in=period_types
    ).exclude(platform__isnull=True).exclude(platform='')  # Only use platform-specific snapshots
    
    # Headline metrics: the latest tracking date in the window, NOT every date
    # summed. See latest_day_total() for why stacking was wrong.
    total_mentions = latest_day_total(snapshot_qs, 'mentions')
    total_citations = latest_day_total(snapshot_qs, 'citations')

    # Previous period, measured the same way so the change is like-for-like.
    prev_total_mentions = latest_day_total(prev_snapshot_qs, 'mentions')
    prev_total_citations = latest_day_total(prev_snapshot_qs, 'citations')
    
    # Calculate weighted average position and visibility score
    # First check if we have snapshots with actual mentions
    snapshot_count = snapshot_qs.count()
    total_mentions_for_avg = sum(snapshot.mentions for snapshot in snapshot_qs)
    
    logger.info(f"Dashboard API: snapshot_count: {snapshot_count}, total_mentions_for_avg: {total_mentions_for_avg}")
    
    # Prepare datetime for raw analytics fallback
    # Use start of day for start_date and end of day for end_date to include all data
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    
    logger.info(f"Dashboard API: Using snapshots: {snapshot_count > 0 and total_mentions_for_avg > 0}")
    
    if snapshot_count > 0 and total_mentions_for_avg > 0:
        # Use snapshots - they have data
        # Weighted average: sum(avg_position * mentions) / sum(mentions)
        # Aggregate across all platform-specific snapshots
        weighted_position_sum = sum(
            float(snapshot.average_position or 0) * snapshot.mentions 
            for snapshot in snapshot_qs if snapshot.mentions > 0
        )
        
        avg_position = weighted_position_sum / total_mentions_for_avg
        # Average visibility score (weighted by mentions)
        weighted_visibility_sum = sum(
            float(snapshot.visibility_score or 0) * snapshot.mentions 
            for snapshot in snapshot_qs if snapshot.mentions > 0
        )
        visibility_score = weighted_visibility_sum / total_mentions_for_avg
    else:
        # No snapshots OR snapshots exist but have no mentions - calculate from raw analytics data
        logger.info(f"Dashboard API: No snapshots found or snapshots have no mentions. Falling back to raw analytics.")
        logger.info(f"Dashboard API: Raw analytics query - start_datetime: {start_datetime}, end_datetime: {end_datetime}")
        
        # Get raw analytics for this period
        raw_analytics = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id,
            is_mention=True,
            is_published=True,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).exclude(platform__isnull=True).exclude(platform='')
        
        raw_analytics_count = raw_analytics.count()
        logger.info(f"Dashboard API: Found {raw_analytics_count} raw analytics records for the period")
        
        if raw_analytics.exists():
            # Aggregate metrics from raw analytics
            raw_totals = raw_analytics.aggregate(
                total_mentions=Sum('total_mentions'),
                total_citations=Sum('total_citations'),
                avg_position=Avg('position'),
                avg_sentiment=Avg('sentiment_score')
            )
            
            raw_total_mentions = raw_totals['total_mentions'] or 0
            raw_total_citations = raw_totals['total_citations'] or 0
            avg_position = float(raw_totals['avg_position'] or 0)
            avg_sentiment = float(raw_totals['avg_sentiment'] or 0)
            
            # Update total_mentions and total_citations from raw data
            total_mentions = raw_total_mentions
            total_citations = raw_total_citations
            
            # Calculate visibility score using the same formula as prompt_analytics_processor
            # Import the processor to use its calculation method
            from .prompt_analytics_processor import PromptAnalyticsProcessor
            processor = PromptAnalyticsProcessor(max_concurrent_prompts=1)
            
            visibility_score = float(processor._calculate_visibility_score(
                mentions=raw_total_mentions,
                citations=raw_total_citations,
                sentiment_score=avg_sentiment,
                average_position=avg_position,
                scope='domain'
            ))
        else:
            # No data for this period - return 0 instead of domain defaults
            logger.warning(f"Dashboard API: No raw analytics found for domain {domain_id} in period {start_date} to {end_date}")
            avg_position = 0.0
            visibility_score = 0.0
            total_mentions = 0
            total_citations = 0
    
    # Calculate previous period metrics for change comparison
    prev_snapshot_count = prev_snapshot_qs.count()
    if prev_snapshot_count > 0:
        prev_weighted_position_sum = sum(
            float(snapshot.average_position or 0) * snapshot.mentions 
            for snapshot in prev_snapshot_qs if snapshot.mentions > 0
        )
        prev_total_mentions_for_avg = sum(snapshot.mentions for snapshot in prev_snapshot_qs)
        
        if prev_total_mentions_for_avg > 0:
            prev_avg_position = prev_weighted_position_sum / prev_total_mentions_for_avg
            prev_weighted_visibility_sum = sum(
                float(snapshot.visibility_score or 0) * snapshot.mentions 
                for snapshot in prev_snapshot_qs if snapshot.mentions > 0
            )
            prev_visibility_score = prev_weighted_visibility_sum / prev_total_mentions_for_avg
        else:
            prev_avg_position = 0
            prev_visibility_score = 0
    else:
        prev_avg_position = 0
        prev_visibility_score = 0
    
    # Calculate change percentages (only if previous period has data)
    def calculate_change(current, previous):
        """Calculate percentage change, return None if no previous data"""
        if previous == 0 or previous is None:
            return None
        change = ((current - previous) / previous) * 100
        return round(change, 1)
    
    mentions_change = calculate_change(total_mentions, prev_total_mentions)
    citations_change = calculate_change(total_citations, prev_total_citations)
    visibility_change = calculate_change(visibility_score, prev_visibility_score)
    position_change = calculate_change(avg_position, prev_avg_position)
    
    # Active alerts from domain
    active_alerts = domain.active_alerts or 0
    
    metrics = {
        'total_mentions': int(total_mentions),
        'total_citations': int(total_citations),
        'visibility_score': round(visibility_score, 2),
        'avg_position': int(round(avg_position)) if avg_position > 0 else 0,
        'active_alerts': active_alerts,
        'mentions_change': mentions_change,
        'citations_change': citations_change,
        'visibility_change': visibility_change,
        'position_change': position_change,
    }
    
    # 2. Brand performance - calculate sentiment from snapshots
    # Aggregate sentiment scores weighted by mentions
    total_positive_mentions = 0
    total_neutral_mentions = 0
    total_negative_mentions = 0
    
    for snapshot in snapshot_qs:
        sentiment = float(snapshot.sentiment_score or 0)
        mentions = snapshot.mentions
        
        if sentiment > 0.33:
            total_positive_mentions += mentions
        elif sentiment >= -0.33:
            total_neutral_mentions += mentions
        else:
            total_negative_mentions += mentions
    
    total_sentiment_mentions = total_positive_mentions + total_neutral_mentions + total_negative_mentions
    
    if total_sentiment_mentions > 0:
        positive_pct = round((total_positive_mentions / total_sentiment_mentions) * 100, 2)
        neutral_pct = round((total_neutral_mentions / total_sentiment_mentions) * 100, 2)
        negative_pct = round((total_negative_mentions / total_sentiment_mentions) * 100, 2)
    else:
        positive_pct = neutral_pct = negative_pct = 0
    
    brand = {
        'visibility_score': round(visibility_score, 2),
        'total_mentions': int(total_mentions),
        'avg_position': int(round(avg_position)) if avg_position > 0 else 0,
        'sentiment': {
            'positive_percentage': positive_pct,
            'neutral_percentage': neutral_pct,
            'negative_percentage': negative_pct
        }
    }
    
    # 3. Platform distribution - use PromptGroupMetricSnapshot for platform breakdown
    # Get platform-specific snapshots (with fallback to more granular period_types)
    platform_snapshots = PromptGroupMetricSnapshot.objects.filter(
        prompt_group__domain_id=domain_id,
        snapshot_date__gte=start_date,
        snapshot_date__lte=end_date,
        period_type__in=period_types
    ).exclude(platform__isnull=True).exclude(platform='')
    
    # Aggregate by platform
    platform_aggregates = {}
    for snapshot in platform_snapshots:
        platform = snapshot.platform
        if platform not in platform_aggregates:
            platform_aggregates[platform] = {
                'mention_count': 0,
                'citations': 0,
                'position_sum': 0,
                'position_weight': 0
            }
        
        platform_aggregates[platform]['mention_count'] += snapshot.mentions
        platform_aggregates[platform]['citations'] += snapshot.citations
        if snapshot.average_position and snapshot.mentions > 0:
            platform_aggregates[platform]['position_sum'] += float(snapshot.average_position) * snapshot.mentions
            platform_aggregates[platform]['position_weight'] += snapshot.mentions
    
    # Build platforms list with weighted averages
    platforms = []
    for platform, agg in platform_aggregates.items():
        avg_pos = (agg['position_sum'] / agg['position_weight']) if agg['position_weight'] > 0 else 0
        platforms.append({
            'platform': platform,
            'mention_count': agg['mention_count'],
            'avg_position': int(round(avg_pos)),
            'citations': agg['citations']
        })
    
    # Sort by mention count
    platforms.sort(key=lambda x: x['mention_count'], reverse=True)
    
    # 4. Share of Voice (latest day in range)
    sov_qs = ShareOfVoiceAnalytics.objects.filter(
        domain_id=domain_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )
    
    share_of_voice = None
    if sov_qs.exists():
        latest_day = sov_qs.order_by('-timestamp').first().timestamp
        latest_rows = sov_qs.filter(timestamp=latest_day)

        # Share of voice stores TWO kinds of row per brand: one per AI platform
        # (ChatGPT / Claude / Gemini / Perplexity) AND an aggregate row that
        # already sums those platforms. Reading both returns every brand several
        # times and double-counts the mentions — a domain whose true total is
        # 7,804 was reported as 15,608. Prefer the aggregate rows, which give
        # exactly one row per brand, as the writer's docstring requires
        # ("consumers that want one figure per brand must filter to it").
        #
        # Rows written before the aggregate existed were all stamped
        # platform='ChatGPT', so those domains have a single platform and
        # already carry one row per brand. Falling back to the unfiltered set
        # keeps them rendering exactly as before instead of showing an empty
        # card — 22 of 41 domains in production are still in that state.
        overall_rows = latest_rows.filter(platform=SOV_OVERALL_PLATFORM)
        if overall_rows.exists():
            latest_rows = overall_rows

        your_brand = latest_rows.filter(competitor__isnull=True).first()
        competitors_rows = latest_rows.filter(
            competitor__isnull=False
        ).order_by('market_position')
        
        competitors_list = []
        for comp_row in competitors_rows:
            try:
                competitor = Competitor.objects.get(id=comp_row.competitor_id)
                competitors_list.append({
                    'competitor_id': comp_row.competitor_id,
                    'name': competitor.name,
                    'url': competitor.url,
                    'share_percentage': float(comp_row.share_percentage),
                    'mention_count': comp_row.mention_count,
                    'market_position': comp_row.market_position,
                    'trend': 0  # TODO: Calculate trend if needed
                })
            except Competitor.DoesNotExist:
                continue
        
        share_of_voice = {
            'date': latest_day.isoformat() if latest_day else None,
            'your_brand': {
                'share_percentage': float(your_brand.share_percentage) if your_brand else 0,
                'mention_count': your_brand.mention_count if your_brand else 0,
                'market_position': 1
            } if your_brand else None,
            'competitors': competitors_list
        }
    
    # 5. Trends - use metric snapshots for time-series data
    trends = []
    
    # Get all snapshots ordered by date
    trend_snapshots = snapshot_qs.order_by('snapshot_date')
    
    # Group by snapshot_date for the selected period_type
    snapshot_by_date = {}
    for snapshot in trend_snapshots:
        snapshot_date = snapshot.snapshot_date
        if snapshot_date not in snapshot_by_date:
            snapshot_by_date[snapshot_date] = {
                'mentions': 0,
                'visibility_sum': 0,
                'visibility_weight': 0
            }
        
        snapshot_by_date[snapshot_date]['mentions'] += snapshot.mentions
        if snapshot.visibility_score and snapshot.mentions > 0:
            snapshot_by_date[snapshot_date]['visibility_sum'] += float(snapshot.visibility_score) * snapshot.mentions
            snapshot_by_date[snapshot_date]['visibility_weight'] += snapshot.mentions
    
    # Build trends array
    for snapshot_date in sorted(snapshot_by_date.keys()):
        data = snapshot_by_date[snapshot_date]
        day_mentions = data['mentions']
        day_visibility = (
            data['visibility_sum'] / data['visibility_weight'] 
            if data['visibility_weight'] > 0 else 0
        )
        
        trends.append({
            'date': format_date_for_chart(snapshot_date),
            'mentions': day_mentions,
            'visibility': round(day_visibility, 2)
        })
    
    # If no snapshots, create empty trend points for the date range
    if not trends:
        current_date = start_date
        while current_date <= end_date:
            trends.append({
                'date': format_date_for_chart(current_date),
                'mentions': 0,
                'visibility': 0
            })
            if period_type == 'daily':
                current_date += timedelta(days=1)
            elif period_type == 'weekly':
                current_date += timedelta(days=7)
            else:  # monthly
                # Approximate month increment
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, current_date.day)
                else:
                    current_date = date(current_date.year, current_date.month + 1, current_date.day)
    
    # 6. Recent mentions - use PromptAnalytics for real-time recent data
    # This is the only part that still uses raw analytics (for recent activity)
    # Use the same datetime range as calculated above for consistency
    # end_datetime and start_datetime are already calculated above
    # Show all mentions regardless of position
    
    recent_analytics = PromptAnalytics.objects.filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        created_at__gte=start_datetime,
        created_at__lte=end_datetime
    ).order_by('-created_at')[:10]
    
    recent_mentions = []
    for a in recent_analytics:
        position = int(round(float(a.position or 0)))
        recent_mentions.append({
            'id': a.id,
            'platform': a.platform,
            'prompt': a.prompt.prompt if a.prompt else '',
            'position': position,
            'sentiment': get_sentiment_category(a.sentiment_score),
            'sentiment_score': float(a.sentiment_score or 0),
            'created_at': a.created_at.isoformat(),
            'relative_time': calculate_relative_time(a.created_at),
            'citations': int(a.total_citations or 0)
        })
    
    return Response({
        'period_days': days,
        'metrics': metrics,
        'brand': brand,
        'platforms': platforms,
        'share_of_voice': share_of_voice,
        'trends': trends,
        'recent_mentions': recent_mentions
    })

