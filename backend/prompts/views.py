from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Prompt, PromptAnalytics


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentions(request):
    """
    Get mentions from PromptAnalytics where is_mention=True
    """
    # Get analytics records that are mentions
    mentions = PromptAnalytics.objects.filter(is_mention=True)
    
    # Apply organization filter if user is not superuser
    if not request.user.is_superuser:
        mentions = mentions.filter(organisation=request.user.organisation)
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        mentions = mentions.filter(
            Q(prompt__prompt__icontains=search_query) |
            Q(context_summary__icontains=search_query) |
            Q(domain__name__icontains=search_query)
        )
    
    # Apply platform filter if provided
    platform = request.GET.get('platform', '')
    if platform and platform != 'all' and platform != 'All Platforms':
        mentions = mentions.filter(platform__icontains=platform)
    
    # Apply sentiment filter if provided
    sentiment = request.GET.get('sentiment', '')
    if sentiment and sentiment != 'all' and sentiment != 'All Sentiments':
        mentions = mentions.filter(sentiment=sentiment)
    
    # Order by most recent first
    mentions = mentions.order_by('-created_at')
    
    # Prepare response data
    mentions_data = []
    for mention in mentions:
        # Structure citations for frontend display
        citations_data = []
        if mention.citations:
            for i, citation in enumerate(mention.citations):
                citations_data.append({
                    'id': i + 1,
                    'text': citation.get('text', ''),
                    'source': citation.get('source', ''),
                    'url': citation.get('url', ''),
                    'description': citation.get('description', '')
                })
        
        mention_data = {
            'id': mention.id,
            'rank': len(mentions_data) + 1,  # Simple ranking based on order
            'mention_text_short': mention.prompt.prompt[:50] + '...' if len(mention.prompt.prompt) > 50 else mention.prompt.prompt,
            'mention_text_long': mention.prompt.prompt,
            'description': mention.context_summary or '',
            'platform': mention.platform,
            'sentiment': mention.sentiment,
            'sentiment_score': float(mention.sentiment_score),
            'total_mentions': mention.total_mentions,
            'total_citations': mention.total_citations,
            'position': float(mention.position),
            'timestamp': mention.created_at.isoformat(),
            'time_ago': _get_time_ago(mention.created_at),
            'domain_name': mention.domain.name,
            'domain_url': mention.domain.url,
            'cluster_id': mention.prompt.cluster.cluster_id,
            'track_status': mention.prompt.track_status,
            'type': mention.prompt.type,
            'citations': citations_data,
            'citations_count': len(citations_data)
        }
        mentions_data.append(mention_data)
    
    return Response({
        'mentions': mentions_data,
        'total_count': len(mentions_data),
        'filters_applied': {
            'search': search_query,
            'platform': platform,
            'sentiment': sentiment
        },
        'available_platforms': _get_available_platforms(),
        'available_sentiments': _get_available_sentiments()
    })


def _get_time_ago(created_at):
    """Helper function to get human-readable time ago"""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    diff = now - created_at
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def _get_available_platforms():
    """Get list of available platforms for filtering"""
    platforms = PromptAnalytics.objects.filter(is_mention=True).values_list('platform', flat=True).distinct()
    return list(platforms)


def _get_available_sentiments():
    """Get list of available sentiments for filtering"""
    sentiments = PromptAnalytics.objects.filter(is_mention=True).values_list('sentiment', flat=True).distinct()
    return list(sentiments)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mention_filters(request):
    """
    Get available filter options for mentions
    """
    # Apply organization filter if user is not superuser
    base_query = PromptAnalytics.objects.filter(is_mention=True)
    if not request.user.is_superuser:
        base_query = base_query.filter(organisation=request.user.organisation)
    
    # Get available platforms
    platforms = list(base_query.values_list('platform', flat=True).distinct())
    
    # Get available sentiments
    sentiments = list(base_query.values_list('sentiment', flat=True).distinct())
    
    # Get total counts by platform
    platform_counts = {}
    for platform in platforms:
        count = base_query.filter(platform=platform).count()
        platform_counts[platform] = count
    
    # Get total counts by sentiment
    sentiment_counts = {}
    for sentiment in sentiments:
        count = base_query.filter(sentiment=sentiment).count()
        sentiment_counts[sentiment] = count
    
    return Response({
        'platforms': [
            {'name': platform, 'count': platform_counts.get(platform, 0)}
            for platform in platforms
        ],
        'sentiments': [
            {'name': sentiment, 'count': sentiment_counts.get(sentiment, 0)}
            for sentiment in sentiments
        ],
        'total_mentions': base_query.count()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mention_detail(request, analytics_id):
    """
    Get detailed information for a specific mention (PromptAnalytics record)
    """
    try:
        # Get the specific analytics record
        analytics_record = get_object_or_404(PromptAnalytics, id=analytics_id)
        
        # Apply organization filter if user is not superuser
        if not request.user.is_superuser:
            if analytics_record.organisation != request.user.organisation:
                return Response(
                    {'error': 'You do not have permission to access this mention.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get related objects
        prompt = analytics_record.prompt
        domain = analytics_record.domain
        cluster = prompt.cluster if prompt.cluster else None
        
        # Structure citations for detailed display
        citations_data = []
        if analytics_record.citations:
            for i, citation in enumerate(analytics_record.citations):
                citations_data.append({
                    'id': i + 1,
                    'text': citation.get('text', ''),
                    'source_name': citation.get('source_name', citation.get('source', '')),
                    'source_url': citation.get('source_url', citation.get('url', '')),
                    'description': citation.get('description', ''),
                    'reliability': citation.get('reliability', 'Unknown'),
                    'referenced_at': citation.get('referenced_at', analytics_record.created_at.isoformat())
                })
        
        # Prepare comprehensive response data
        response_data = {
            # Basic mention info
            'id': analytics_record.id,
            'rank': 1,  # This would need to be calculated based on position/score
            'platform': analytics_record.platform,
            'sentiment': analytics_record.sentiment,
            'sentiment_score': float(analytics_record.sentiment_score),
            'created_at': analytics_record.created_at.isoformat(),
            'time_ago': _get_time_ago(analytics_record.created_at),
            
            # Prompt details
            'prompt_text': prompt.prompt,
            'prompt_text_short': prompt.prompt[:100] + '...' if len(prompt.prompt) > 100 else prompt.prompt,
            'full_ai_response': analytics_record.context_summary or '',
            
            # Metrics
            'total_mentions': analytics_record.total_mentions,
            'total_citations': analytics_record.total_citations,
            'position': float(analytics_record.position),
            'is_mention': analytics_record.is_mention,
            
            # Tracking info
            'track_status': prompt.track_status,
            'type': prompt.type,
            'last_tracked_at': prompt.last_tracked_at.isoformat() if prompt.last_tracked_at else None,
            'track_message': prompt.track_message,
            
            # Domain and cluster info
            'domain_name': domain.name,
            'domain_url': domain.url,
            'cluster_id': cluster.cluster_id if cluster else None,
            
            # Citations with detailed structure
            'citations': citations_data,
            'citations_count': len(citations_data),
            
            # Engagement metrics (currently missing from model)
            'views': None,  # MISSING FIELD - needs to be added to PromptAnalytics
            'shares': None,  # MISSING FIELD - needs to be added to PromptAnalytics
            
            # Historical data (would need separate endpoint)
            'position_trend': [],  # MISSING - needs historical position data
            'key_topics': [],  # MISSING - needs topic extraction or keyword association
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve mention details: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

