from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Avg, Count

from prompts.models import PromptAnalytics
from alerts.models import Alert
from .models import SentimentAnalytics, ShareOfVoiceAnalytics


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    domain_id = request.query_params.get('domain_id')
    days = int(request.query_params.get('days', 7))

    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    start_dt = now - timedelta(days=days)

    # Mentions
    mentions_qs = PromptAnalytics.objects.filter(
        prompt__group__domain_id=domain_id,
        is_mention=True,
        is_published=True,
        created_at__gte=start_dt
    )
    mentions_total = mentions_qs.count()
    platforms = list(mentions_qs.values('platform').annotate(count=Count('id')).order_by('-count'))
    avg_position = float(mentions_qs.aggregate(v=Avg('position'))['v'] or 0)
    avg_sentiment = float(mentions_qs.aggregate(v=Avg('sentiment_score'))['v'] or 0)

    # Alerts (last X days)
    alerts_qs = Alert.objects.filter(domain_id=domain_id, created_at__gte=start_dt)
    alerts_summary = list(
        alerts_qs.values('type', 'severity', 'status').annotate(count=Count('id')).order_by('-count')
    )
    active_alerts = alerts_qs.filter(status='active').count()

    # Sentiment (weighted)
    senti_qs = SentimentAnalytics.objects.filter(domain_id=domain_id, snapshot_date__gte=start_dt.date())
    total_mentions = senti_qs.aggregate(Sum('mention_count'))['mention_count__sum'] or 0
    if total_mentions > 0:
        weighted = lambda fld: sum(getattr(x, fld) * x.mention_count for x in senti_qs) / total_mentions
        sentiment_summary = {
            'positive_percentage': round(weighted('positive_percentage'), 2),
            'neutral_percentage': round(weighted('neutral_percentage'), 2),
            'negative_percentage': round(weighted('negative_percentage'), 2),
            'total_mentions': total_mentions,
        }
    else:
        sentiment_summary = {
            'positive_percentage': 0,
            'neutral_percentage': 0,
            'negative_percentage': 0,
            'total_mentions': 0,
        }

    # Share of Voice (latest day in range)
    sov_qs = ShareOfVoiceAnalytics.objects.filter(domain_id=domain_id, timestamp__gte=start_dt.date())
    latest_sov = None
    if sov_qs.exists():
        latest_day = sov_qs.order_by('-timestamp').first().timestamp
        latest_rows = sov_qs.filter(timestamp=latest_day)
        your_brand = latest_rows.filter(competitor__isnull=True).first()
        competitors = latest_rows.filter(competitor__isnull=False).order_by('market_position')
        latest_sov = {
            'date': latest_day.isoformat(),
            'your_brand': {
                'share_percentage': float(getattr(your_brand, 'share_percentage', 0) or 0),
                'mention_count': getattr(your_brand, 'mention_count', 0) or 0,
            } if your_brand else None,
            'competitors': [
                {
                    'competitor_id': r.competitor_id,
                    'share_percentage': float(r.share_percentage),
                    'mention_count': r.mention_count,
                    'market_position': r.market_position,
                    'platform': r.platform
                } for r in competitors
            ]
        }

    # Top mentions (by engagement or recent)
    top_mentions = mentions_qs.order_by('-engagement_score', '-created_at')[:10]
    top_mentions_data = [{
        'id': m.id,
        'prompt': m.prompt.prompt,
        'platform': m.platform,
        'position': float(m.position),
        'sentiment_score': float(m.sentiment_score),
        'engagement_score': float(m.engagement_score),
        'created_at': m.created_at.isoformat(),
    } for m in top_mentions]

    return Response({
        'period_days': days,
        'mentions': {
            'total': mentions_total,
            'avg_position': round(avg_position, 2),
            'avg_sentiment': round(avg_sentiment, 3),
            'by_platform': platforms,
            'top_mentions': top_mentions_data,
        },
        'alerts': {
            'active': active_alerts,
            'summary': alerts_summary,
        },
        'sentiment': sentiment_summary,
        'share_of_voice_latest': latest_sov,
    })


