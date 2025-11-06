from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q
from datetime import timedelta, datetime
from shared_models.models import (
    Domain, PromptAnalytics, ShareOfVoiceAnalytics, Competitor
)


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


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_summary(request):
    """
    Get comprehensive dashboard data for a domain, filtered by days.
    
    Query Parameters:
    - domain_id (required): Domain ID
    - days (optional, default=30): Number of days to look back (7, 30, 90, etc.)
    """
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
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # 1. Get metrics from PromptAnalytics (filtered by date range)
    analytics_qs = PromptAnalytics.objects.filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    total_mentions = analytics_qs.count()
    total_citations = analytics_qs.aggregate(
        total=Sum('total_citations')
    )['total'] or 0
    avg_position = float(
        analytics_qs.aggregate(avg=Avg('position'))['avg'] or 0
    )
    
    # Visibility score from domain (or calculate from mentions)
    visibility_score = float(domain.visibility_score or 0)
    
    # Active alerts from domain
    active_alerts = domain.active_alerts or 0
    
    metrics = {
        'total_mentions': total_mentions,
        'total_citations': int(total_citations),
        'visibility_score': round(visibility_score, 2),
        'avg_position': round(avg_position, 2) if avg_position > 0 else 0,
        'active_alerts': active_alerts
    }
    
    # 2. Brand performance
    # Calculate sentiment breakdown
    positive_count = analytics_qs.filter(
        sentiment_score__gt=0.33
    ).count()
    neutral_count = analytics_qs.filter(
        sentiment_score__gte=-0.33,
        sentiment_score__lte=0.33
    ).count()
    negative_count = analytics_qs.filter(
        sentiment_score__lt=-0.33
    ).count()
    
    total_sentiment = positive_count + neutral_count + negative_count
    if total_sentiment > 0:
        positive_pct = round((positive_count / total_sentiment) * 100, 2)
        neutral_pct = round((neutral_count / total_sentiment) * 100, 2)
        negative_pct = round((negative_count / total_sentiment) * 100, 2)
    else:
        positive_pct = neutral_pct = negative_pct = 0
    
    brand = {
        'visibility_score': round(visibility_score, 2),
        'total_mentions': total_mentions,
        'avg_position': round(avg_position, 2) if avg_position > 0 else 0,
        'sentiment': {
            'positive_percentage': positive_pct,
            'neutral_percentage': neutral_pct,
            'negative_percentage': negative_pct
        }
    }
    
    # 3. Platform distribution with avg positions (filtered by date range)
    platforms_data = analytics_qs.values('platform').annotate(
        mention_count=Count('id'),
        avg_position=Avg('position'),
        citations=Sum('total_citations')
    ).order_by('-mention_count')
    
    platforms = []
    for p in platforms_data:
        platforms.append({
            'platform': p['platform'],
            'mention_count': p['mention_count'],
            'avg_position': round(float(p['avg_position'] or 0), 2) if p['avg_position'] else 0,
            'citations': int(p['citations'] or 0)
        })
    
    # 4. Share of Voice (latest day in range)
    sov_qs = ShareOfVoiceAnalytics.objects.filter(
        domain_id=domain_id,
        timestamp__gte=start_date.date(),
        timestamp__lte=end_date.date()
    )
    
    share_of_voice = None
    if sov_qs.exists():
        latest_day = sov_qs.order_by('-timestamp').first().timestamp
        latest_rows = sov_qs.filter(timestamp=latest_day)
        
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
    
    # 5. Trends - daily data (filtered by date range)
    trends = []
    current_date = start_date.date()
    end_date_only = end_date.date()
    
    while current_date <= end_date_only:
        day_start = timezone.make_aware(
            datetime.combine(current_date, datetime.min.time())
        )
        day_end = timezone.make_aware(
            datetime.combine(current_date, datetime.max.time())
        )
        
        day_analytics = analytics_qs.filter(
            created_at__gte=day_start,
            created_at__lte=day_end
        )
        
        day_mentions = day_analytics.count()
        day_avg_position = float(
            day_analytics.aggregate(avg=Avg('position'))['avg'] or 0
        )
        day_avg_sentiment = float(
            day_analytics.aggregate(avg=Avg('sentiment_score'))['avg'] or 0
        )
        
        # Calculate visibility score for the day (based on position and sentiment)
        # Visibility = (inverse position score + sentiment score) / 2 * 100
        if day_avg_position > 0:
            position_score = max(0, (10 - day_avg_position) / 10)  # 0-1 scale
            sentiment_score = (day_avg_sentiment + 1) / 2  # -1 to 1 -> 0 to 1
            day_visibility = ((position_score + sentiment_score) / 2) * 100
        else:
            day_visibility = 0
        
        trends.append({
            'date': format_date_for_chart(current_date),
            'mentions': day_mentions,
            'visibility': round(day_visibility, 2)
        })
        
        current_date += timedelta(days=1)
    
    # 6. Recent mentions (filtered by date range, last 20)
    recent_analytics = analytics_qs.order_by('-created_at')[:20]
    
    recent_mentions = []
    for a in recent_analytics:
        recent_mentions.append({
            'id': a.id,
            'platform': a.platform,
            'prompt': a.prompt.prompt if a.prompt else '',
            'position': float(a.position or 0),
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

