from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Avg, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta, datetime
from .models import PromptGroup, Prompt, PromptAnalytics
from domains.models import Domain, DomainAccess
from .serializers import PromptAnalyticsSerializer, PromptGroupSerializer, PromptSerializer
import json


@api_view(['GET'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def get_mentions(request):
    """
    Get mentions from PromptAnalytics where is_mention=True and is_published=True
    """
    # Require domain_id and access check
    domain_id = request.GET.get('domain_id')
    if not domain_id:
        return Response({
            'mentions': [],
            'total_count': 0,
            'filters_applied': {
                'search': request.GET.get('search', ''),
                'platform': request.GET.get('platform', ''),
                'sentiment': request.GET.get('sentiment', ''),
                'domain_id': None,
            },
            'available_platforms': ['ChatGPT', 'Google Gemini', 'Perplexity'],
            'available_sentiments': ['Positive', 'Negative', 'Neutral']
        })

    user = getattr(request, 'user', None)
    has_access = False
    if user and getattr(user, 'is_authenticated', False):
        if getattr(user, 'role', '') == 'super_admin':
            has_access = True
        else:
            has_access = DomainAccess.objects.filter(user=user, domain_id=domain_id).exists()
    if not has_access:
        return Response({'error': 'Forbidden: no access to this domain.'}, status=status.HTTP_403_FORBIDDEN)

    # Get analytics records that are mentions and published for this domain
    mentions = PromptAnalytics.objects.filter(is_mention=True, is_published=True, domain_id=domain_id)
    
    # Apply organization filter if user is authenticated and not superuser
    # Temporarily skip organization filtering for testing
    # if hasattr(request, 'user') and request.user.is_authenticated and not request.user.is_superuser:
    #     mentions = mentions.filter()
    
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
    if sentiment and sentiment.lower() != 'all' and sentiment.lower() != 'all sentiments':
        mentions = mentions.filter(sentiment__iexact=sentiment)
    
    # Order by most recent first
    mentions = mentions.order_by('-created_at')

    # Pagination
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
    except ValueError:
        limit = 20
        offset = 0
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    total_count = mentions.count()
    mentions = mentions[offset:offset + limit]
    
    # Prepare response data
    mentions_data = []
    for mention in mentions:
        # For now, citations are disabled and returned as an empty array
        citations_data = []
        
        mention_data = {
            'id': mention.id,
            'rank': len(mentions_data) + 1,  # Simple ranking based on order
            'mention_text_short': mention.prompt.prompt[:50] + '...' if len(mention.prompt.prompt) > 50 else mention.prompt.prompt,
            'mention_text_long': mention.prompt.prompt,
            'description': (mention.context_summary[:500] + '...') if mention.context_summary and len(mention.context_summary) > 500 else (mention.context_summary or ''),
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
            'group_id': mention.prompt.group.group_id if mention.prompt.group else None,
            'track_status': mention.prompt.track_status,
            'type': mention.prompt.type,
            'citations': citations_data,
            'citations_count': len(citations_data),
            'views': mention.views,
            'shares': mention.shares,
            'engagement_score': float(mention.engagement_score),
            'competitor_mentions': mention.competitor_mentions,
            'key_topics': mention.key_topics
        }
        mentions_data.append(mention_data)
    
    return Response({
        'mentions': mentions_data,
        'total_count': total_count,
        'filters_applied': {
            'search': search_query,
            'platform': platform,
            'sentiment': sentiment,
            'domain_id': domain_id
        },
        'pagination': {
            'limit': limit,
            'offset': offset,
            'returned': len(mentions_data)
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
    platforms = PromptAnalytics.objects.filter(is_mention=True, is_published=True).values_list('platform', flat=True).distinct()
    return list(platforms)


def _get_available_sentiments():
    """Get list of available sentiments for filtering"""
    sentiments = PromptAnalytics.objects.filter(is_mention=True, is_published=True).values_list('sentiment', flat=True).distinct()
    return list(sentiments)


@api_view(['GET'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def get_mention_filters(request):
    """
    Get available filter options for mentions
    """
    # Apply organization filter if user is not superuser
    base_query = PromptAnalytics.objects.filter(is_mention=True, is_published=True)
    # Temporarily skip organization filtering for testing
    # if not request.user.is_superuser:
    #     base_query = base_query.filter()
    
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
@permission_classes([AllowAny])  # Temporarily allow all for testing
def get_mention_detail(request, analytics_id):
    """
    Get detailed information for a specific mention (PromptAnalytics record)
    """
    try:
        # Get the specific analytics record
        analytics_record = get_object_or_404(PromptAnalytics, id=analytics_id)
        
        # Apply organization filter if user is not superuser
        # Temporarily disabled for testing
        # if not request.user.is_superuser:
        #     if analytics_record.organisation != request.user.organisation:
        #         return Response(
        #             {'error': 'You do not have permission to access this mention.'},
        #             status=status.HTTP_403_FORBIDDEN
        #         )
        
        # Get related objects
        prompt = analytics_record.prompt
        domain = analytics_record.domain
        group = prompt.group if prompt.group else None
        
        # Structure citations for detailed display
        citations_data = []
        if analytics_record.citations:
            # Handle both string and list citations
            if isinstance(analytics_record.citations, str):
                # If citations is a string, treat it as a single citation
                citations_data.append({
                    'id': 1,
                    'text': analytics_record.citations,
                    'source_name': 'Source',
                    'source_url': '',
                    'description': '',
                    'reliability': 'Unknown',
                    'referenced_at': analytics_record.created_at.isoformat()
                })
            elif isinstance(analytics_record.citations, list):
                for i, citation in enumerate(analytics_record.citations):
                    if isinstance(citation, dict):
                        citations_data.append({
                            'id': i + 1,
                            'text': citation.get('text', ''),
                            'source_name': citation.get('source_name', citation.get('source', '')),
                            'source_url': citation.get('source_url', citation.get('url', '')),
                            'description': citation.get('description', ''),
                            'reliability': citation.get('reliability', 'Unknown'),
                            'referenced_at': citation.get('referenced_at', analytics_record.created_at.isoformat())
                        })
                    else:
                        # Handle string citations in list
                        citations_data.append({
                            'id': i + 1,
                            'text': str(citation),
                            'source_name': 'Source',
                            'source_url': '',
                            'description': '',
                            'reliability': 'Unknown',
                            'referenced_at': analytics_record.created_at.isoformat()
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
            'last_tracked_at': prompt.tracked_at.isoformat() if prompt.tracked_at else None,
            'track_message': prompt.track_message,
            
            # Domain and group info
            'domain_name': domain.name,
            'domain_url': domain.url,
            'group_id': group.group_id if group else None,
            
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mention_trends(request):
    """
    Get mention trends over time for analytics
    """
    try:
        # Get date range from query params
        days = int(request.GET.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get mentions for the organization
        mentions = PromptAnalytics.objects.filter(
            is_mention=True,
            is_published=True,
            # organisation__isnull=True,  # Temporarily disabled for testing
            created_at__range=[start_date, end_date]
        )
        
        # Group by date and platform
        trends_data = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            day_mentions = mentions.filter(created_at__date=current_date.date())
            
            platform_data = {}
            for platform in ['ChatGPT', 'Claude', 'Perplexity', 'Gemini', 'Grok']:
                platform_mentions = day_mentions.filter(platform=platform)
                platform_data[platform.lower()] = {
                    'count': platform_mentions.count(),
                    'avg_position': float(platform_mentions.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0),
                    'avg_sentiment': float(platform_mentions.aggregate(avg_sent=Avg('sentiment_score'))['avg_sent'] or 0)
                }
            
            trends_data.append({
                'date': date_str,
                'total_mentions': day_mentions.count(),
                'avg_position': float(day_mentions.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0),
                'platforms': platform_data
            })
            
            current_date += timedelta(days=1)
        
        return Response({
            'trends': trends_data,
            'period': f'{days} days',
            'total_mentions': mentions.count()
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve mention trends: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mention_analytics(request):
    """
    Get comprehensive analytics for mentions
    """
    try:
        # Get mentions for the organization
        mentions = PromptAnalytics.objects.filter(
            is_mention=True,
            is_published=True
        )
        
        # Platform breakdown
        platform_stats = mentions.values('platform').annotate(
            count=Count('id'),
            avg_position=Avg('position'),
            avg_sentiment=Avg('sentiment_score'),
            total_views=Count('views'),
            total_shares=Count('shares')
        ).order_by('-count')
        
        # Sentiment breakdown
        sentiment_stats = mentions.values('sentiment').annotate(
            count=Count('id'),
            avg_position=Avg('position'),
            avg_sentiment_score=Avg('sentiment_score')
        ).order_by('-count')
        
        # Top performing mentions
        top_mentions = mentions.order_by('-engagement_score')[:10]
        top_mentions_data = []
        for mention in top_mentions:
            top_mentions_data.append({
                'id': mention.id,
                'prompt_text': mention.prompt.prompt[:100] + '...' if len(mention.prompt.prompt) > 100 else mention.prompt.prompt,
                'platform': mention.platform,
                'position': float(mention.position),
                'sentiment': mention.sentiment,
                'engagement_score': float(mention.engagement_score),
                'views': mention.views,
                'shares': mention.shares,
                'created_at': mention.created_at.isoformat()
            })
        
        # Competitor analysis
        competitor_data = {}
        for mention in mentions:
            if mention.competitor_mentions:
                for competitor in mention.competitor_mentions:
                    if competitor not in competitor_data:
                        competitor_data[competitor] = {'count': 0, 'mentions': []}
                    competitor_data[competitor]['count'] += 1
                    competitor_data[competitor]['mentions'].append({
                        'id': mention.id,
                        'platform': mention.platform,
                        'sentiment': mention.sentiment,
                        'position': float(mention.position)
                    })
        
        return Response({
            'platform_stats': list(platform_stats),
            'sentiment_stats': list(sentiment_stats),
            'top_mentions': top_mentions_data,
            'competitor_analysis': competitor_data,
            'total_mentions': mentions.count(),
            'avg_position': float(mentions.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0),
            'avg_sentiment': float(mentions.aggregate(avg_sent=Avg('sentiment_score'))['avg_sent'] or 0)
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve mention analytics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def get_related_mentions(request, analytics_id):
    """
    Get related mentions for a specific mention
    """
    try:
        # Get the original mention
        original_mention = get_object_or_404(PromptAnalytics, id=analytics_id)
        
        # Apply organization filter
        if original_mention.organisation != request.user.organisation:
            return Response(
                {'error': 'You do not have permission to access this mention.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Find related mentions based on similar prompts or same group
        related_mentions = PromptAnalytics.objects.filter(
            is_mention=True,
            is_published=True
        ).exclude(id=analytics_id)
        
        # Filter by same group first (only if the original mention has a group)
        same_group_mentions = []
        if original_mention.prompt.group:
            same_group_mentions = related_mentions.filter(
                prompt__group=original_mention.prompt.group
            ).order_by('-created_at')[:5]
        
        # Filter by similar platform
        same_platform_mentions = related_mentions.filter(
            platform=original_mention.platform
        )
        if original_mention.prompt.group:
            same_platform_mentions = same_platform_mentions.exclude(prompt__group=original_mention.prompt.group)
        same_platform_mentions = same_platform_mentions.order_by('-created_at')[:3]
        
        # Combine and format results
        related_data = []
        for mention in same_group_mentions:
            related_data.append({
                'id': mention.id,
                'prompt_text': mention.prompt.prompt[:100] + '...' if len(mention.prompt.prompt) > 100 else mention.prompt.prompt,
                'platform': mention.platform,
                'position': float(mention.position),
                'sentiment': mention.sentiment,
                'created_at': mention.created_at.isoformat(),
                'time_ago': _get_time_ago(mention.created_at),
                'relation_type': 'same_group'
            })
        
        for mention in same_platform_mentions:
            related_data.append({
                'id': mention.id,
                'prompt_text': mention.prompt.prompt[:100] + '...' if len(mention.prompt.prompt) > 100 else mention.prompt.prompt,
                'platform': mention.platform,
                'position': float(mention.position),
                'sentiment': mention.sentiment,
                'created_at': mention.created_at.isoformat(),
                'time_ago': _get_time_ago(mention.created_at),
                'relation_type': 'same_platform'
            })
        
        return Response({
            'related_mentions': related_data,
            'original_mention': {
                'id': original_mention.id,
                'prompt_text': original_mention.prompt.prompt,
                'platform': original_mention.platform,
                'group_id': original_mention.prompt.group.group_id if original_mention.prompt.group else None
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve related mentions: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_mentions(request):
    """
    Export mentions data
    """
    try:
        # Get filter parameters
        platform = request.data.get('platform', '')
        sentiment = request.data.get('sentiment', '')
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        export_format = request.data.get('format', 'csv')
        
        # Build query
        mentions = PromptAnalytics.objects.filter(
            is_mention=True,
            is_published=True
        )
        
        if platform and platform != 'all':
            mentions = mentions.filter(platform__icontains=platform)
        
        if sentiment and sentiment != 'all':
            mentions = mentions.filter(sentiment=sentiment)
        
        if date_from:
            mentions = mentions.filter(created_at__gte=date_from)
        
        if date_to:
            mentions = mentions.filter(created_at__lte=date_to)
        
        # Prepare export data
        export_data = []
        for mention in mentions:
            export_data.append({
                'id': mention.id,
                'prompt': mention.prompt.prompt,
                'platform': mention.platform,
                'sentiment': mention.sentiment,
                'position': float(mention.position),
                'total_mentions': mention.total_mentions,
                'total_citations': mention.total_citations,
                'views': mention.views,
                'shares': mention.shares,
                'engagement_score': float(mention.engagement_score),
                'created_at': mention.created_at.isoformat(),
                'domain_name': mention.domain.name,
                'group_id': mention.prompt.group.group_id
            })
        
        # For now, return the data (in real implementation, you'd generate actual file)
        return Response({
            'message': 'Export data prepared',
            'format': export_format,
            'count': len(export_data),
            'data': export_data,
            'download_url': f'/api/prompts/mentions/export/download/{len(export_data)}/'  # Placeholder
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to export mentions: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== PROMPTS APIs ====================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def prompt_groups_list(request):
    """
    List all prompt groups for the organization or create a new one
    """
    if request.method == 'GET':
        try:
            # Require domain_id and access
            domain_id = request.GET.get('domain_id')
            if not domain_id:
                return Response({'groups': [], 'total_count': 0, 'filters_applied': {'domain_id': None, 'search': request.GET.get('search', '')}})

            user = getattr(request, 'user', None)
            has_access = False
            if user and getattr(user, 'is_authenticated', False):
                if getattr(user, 'role', '') == 'super_admin':
                    has_access = True
                else:
                    has_access = DomainAccess.objects.filter(user=user, domain_id=domain_id).exists()
            if not has_access:
                return Response({'error': 'Forbidden: no access to this domain.'}, status=status.HTTP_403_FORBIDDEN)

            # Get prompt groups scoped to domain
            groups = PromptGroup.objects.filter(domain_id=domain_id)
            
            # Apply search filter if provided
            search_query = request.GET.get('search', '')
            if search_query:
                groups = groups.filter(
                    Q(group_id__icontains=search_query) |
                    Q(domain__name__icontains=search_query)
                )
            
            # Order by creation date
            groups = groups.order_by('-created_at')

            # Pagination
            try:
                limit = int(request.GET.get('limit', 20))
                offset = int(request.GET.get('offset', 0))
            except ValueError:
                limit = 20
                offset = 0
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            total_count = groups.count()
            groups = groups[offset:offset + limit]
            
            # Prepare response data
            groups_data = []
            for group in groups:
                # Get analytics summary for the group
                analytics = PromptAnalytics.objects.filter(
                    prompt__group=group
                )
                # Derive primary and secondary prompts
                primary_prompt_obj = group.prompts.filter(type='primary').order_by('created_at').first()
                primary_prompt_text = primary_prompt_obj.prompt if primary_prompt_obj else ''
                secondary_prompts_list = list(
                    group.prompts.filter(type='secondary').order_by('created_at').values_list('prompt', flat=True)
                )
                
                groups_data.append({
                    'id': group.id,
                    'group_id': group.group_id,
                    'domain_id': group.domain.id,
                    'domain_name': group.domain.name,
                    'total_mentions': group.total_mentions,
                    'total_citations': group.total_citations,
                    'average_position': float(group.average_position),
                    'created_at': group.created_at.isoformat(),
                    'modified_at': group.modified_at.isoformat(),
                    'prompts_count': group.prompts.count(),
                    'primary_prompt': primary_prompt_text,
                    'secondary_prompts': secondary_prompts_list,
                    'analytics_summary': {
                        'total_analytics': analytics.count(),
                        'mentions_count': analytics.filter(is_mention=True, is_published=True).count(),
                        'avg_position': float(analytics.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0),
                        'platforms': list(analytics.values_list('platform', flat=True).distinct())
                    }
                })
            
            return Response({
                'groups': groups_data,
                'total_count': total_count,
                'filters_applied': {
                    'domain_id': domain_id,
                    'search': search_query
                },
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'returned': len(groups_data)
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve prompt groups: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        try:
            # Validate required fields
            group_id = request.data.get('group_id')
            domain_id = request.data.get('domain_id')
            primary_prompts = request.data.get('primary_prompts', [])
            secondary_prompts = request.data.get('secondary_prompts', [])
            
            if not group_id or not domain_id:
                return Response(
                    {'error': 'group_id and domain_id are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not primary_prompts and not secondary_prompts:
                return Response(
                    {'error': 'At least one primary or secondary prompt is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if group already exists
            if PromptGroup.objects.filter(group_id=group_id, domain_id=domain_id).exists():
                return Response(
                    {'error': 'Prompt group with this ID already exists for this domain'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get domain
            domain = get_object_or_404(Domain, id=domain_id)
            
            # Create new prompt group (attach organisation)
            group = PromptGroup.objects.create(
                group_id=group_id,
                domain=domain,
                organisation=domain.organisation
            )
            
            # Platforms to create analytics for
            platforms = ["ChatGPT", "Google Gemini", "Perplexity"]
            
            # Create prompts and analytics
            created_prompts = []
            created_analytics = []
            
            # Create primary prompts
            for prompt_text in primary_prompts:
                if prompt_text.strip():
                    prompt = Prompt.objects.create(
                        prompt=prompt_text.strip(),
                        group=group,
                        domain=domain,
                        organisation=domain.organisation,
                        track_status='active',
                        type='primary'
                    )
                    created_prompts.append(prompt)
                    
                    # Create analytics for each platform
                    for platform in platforms:
                        analytics = PromptAnalytics.objects.create(
                            prompt=prompt,
                            platform=platform,
                            domain=domain,
                            organisation=domain.organisation,
                            is_mention=False,  # Initially not a mention
                            position=0.0,
                            sentiment='neutral',
                            sentiment_score=0.0,
                            total_mentions=0,
                            total_citations=0
                        )
                        created_analytics.append(analytics)
            
            # Create secondary prompts
            for prompt_text in secondary_prompts:
                if prompt_text.strip():
                    prompt = Prompt.objects.create(
                        prompt=prompt_text.strip(),
                        group=group,
                        domain=domain,
                        organisation=domain.organisation,
                        track_status='active',
                        type='secondary'
                    )
                    created_prompts.append(prompt)
                    
                    # Create analytics for each platform
                    for platform in platforms:
                        analytics = PromptAnalytics.objects.create(
                            prompt=prompt,
                            platform=platform,
                            domain=domain,
                            organisation=domain.organisation,
                            is_mention=False,  # Initially not a mention
                            position=0.0,
                            sentiment='neutral',
                            sentiment_score=0.0,
                            total_mentions=0,
                            total_citations=0
                        )
                        created_analytics.append(analytics)
            
            return Response({
                'message': 'Prompt group created successfully',
                'group': {
                    'id': group.id,
                    'group_id': group.group_id,
                    'domain_id': group.domain.id,
                    'domain_name': group.domain.name,
                    'created_at': group.created_at.isoformat()
                },
                'prompts_created': len(created_prompts),
                'analytics_created': len(created_analytics),
                'platforms': platforms
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create prompt group: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def prompt_group_detail(request, group_id):
    """
    Get, update, or delete a specific prompt group
    """
    try:
        group = get_object_or_404(PromptGroup, id=group_id)
        
        if request.method == 'GET':
            # Get detailed information about the group
            prompts = group.prompts.all().order_by('created_at')
            analytics = PromptAnalytics.objects.filter(
                prompt__group=group
            )

            # Derive primary and secondary prompts for detail view
            primary_prompt_obj = group.prompts.filter(type='primary').order_by('created_at').first()
            primary_prompt_text = primary_prompt_obj.prompt if primary_prompt_obj else ''
            secondary_prompts_list = list(
                group.prompts.filter(type='secondary').order_by('created_at').values_list('prompt', flat=True)
            )
            
            prompts_data = []
            for prompt in prompts:
                prompt_analytics = analytics.filter(prompt=prompt)
                prompts_data.append({
                    'id': prompt.id,
                    'prompt_text': prompt.prompt,
                    'track_status': prompt.track_status,
                    'type': prompt.type,
                    'last_tracked_at': prompt.tracked_at.isoformat() if prompt.tracked_at else None,
                    'track_message': prompt.track_message,
                    'created_at': prompt.created_at.isoformat(),
                    'analytics_count': prompt_analytics.count(),
                    'mentions_count': prompt_analytics.filter(is_mention=True, is_published=True).count(),
                    'avg_position': float(prompt_analytics.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0)
                })
            
            return Response({
                'group': {
                    'id': group.id,
                    'group_id': group.group_id,
                    'domain_id': group.domain.id,
                    'domain_name': group.domain.name,
                    'primary_prompt': primary_prompt_text,
                    'secondary_prompts': secondary_prompts_list,
                    'total_mentions': group.total_mentions,
                    'total_citations': group.total_citations,
                    'average_position': float(group.average_position),
                    'created_at': group.created_at.isoformat(),
                    'modified_at': group.modified_at.isoformat(),
                    'prompts': prompts_data,
                    'analytics_summary': {
                        'total_analytics': analytics.count(),
                        'mentions_count': analytics.filter(is_mention=True, is_published=True).count(),
                        'platforms': list(analytics.values_list('platform', flat=True).distinct()),
                        'sentiments': list(analytics.values_list('sentiment', flat=True).distinct())
                    }
                }
            })
        
        elif request.method == 'PUT':
            # Update group information and prompts (primary + variants)
            group_id_new = request.data.get('group_id', group.group_id)
            domain_id = request.data.get('domain_id', group.domain.id)
            primary_prompt_text = request.data.get('primary_prompt')
            secondary_prompts_texts = request.data.get('secondary_prompts', []) or []

            # Check if new group_id already exists (if changed)
            if group_id_new != group.group_id:
                if PromptGroup.objects.filter(group_id=group_id_new, domain_id=domain_id).exists():
                    return Response(
                        {'error': 'Prompt group with this ID already exists for this domain'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Update group fields
            group.group_id = group_id_new
            group.domain_id = domain_id
            group.save()

            # If primary/secondary provided, reconcile prompts to match
            if primary_prompt_text is not None:
                primary_prompt_text = str(primary_prompt_text).strip()
                # Normalize secondary list (unique, trimmed, exclude empty and primary)
                normalized_secondaries = []
                for s in secondary_prompts_texts:
                    s_norm = str(s).strip()
                    if s_norm and s_norm != primary_prompt_text and s_norm not in normalized_secondaries:
                        normalized_secondaries.append(s_norm)

                # Ensure primary prompt exists and is marked primary
                primary_prompt_obj = group.prompts.filter(prompt=primary_prompt_text).first()
                if primary_prompt_obj:
                    if primary_prompt_obj.type != 'primary':
                        primary_prompt_obj.type = 'primary'
                        primary_prompt_obj.save()
                else:
                    primary_prompt_obj = Prompt.objects.create(
                        prompt=primary_prompt_text,
                        group=group,
                        domain=group.domain,
                        organisation=group.domain.organisation,
                        track_status='active',
                        type='primary'
                    )

                # Upsert secondary prompts
                existing_prompts = {p.prompt: p for p in group.prompts.all()}
                for sec_text in normalized_secondaries:
                    if sec_text in existing_prompts:
                        p = existing_prompts[sec_text]
                        if p.type != 'secondary':
                            p.type = 'secondary'
                            p.save()
                    else:
                        Prompt.objects.create(
                            prompt=sec_text,
                            group=group,
                            domain=group.domain,
                            organisation=group.domain.organisation,
                            track_status='active',
                            type='secondary'
                        )

                # Remove any prompts no longer in the provided set (except keep analytics integrity)
                keep_set = set([primary_prompt_text] + normalized_secondaries)
                for p in group.prompts.exclude(prompt__in=keep_set):
                    p.delete()

                # Ensure only one primary remains
                group.prompts.exclude(id=primary_prompt_obj.id).filter(type='primary').update(type='secondary')

            return Response({
                'message': 'Prompt group updated successfully',
                'group': {
                    'id': group.id,
                    'group_id': group.group_id,
                    'domain_id': group.domain.id,
                    'domain_name': group.domain.name,
                    'modified_at': group.modified_at.isoformat()
                }
            })
        
        elif request.method == 'DELETE':
            # Delete the group (this will cascade delete all prompts and analytics)
            group.delete()
            return Response({
                'message': 'Prompt group deleted successfully'
            })
            
    except Exception as e:
        return Response(
            {'error': f'Failed to process prompt group: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def prompts_list(request):
    """
    List all prompts for the organization or create a new one
    """
    if request.method == 'GET':
        try:
            # Require domain_id and access
            domain_id = request.GET.get('domain_id')
            if not domain_id:
                return Response({'prompts': [], 'total_count': 0, 'filters_applied': {
                    'group_id': request.GET.get('group_id'),
                    'domain_id': None,
                    'track_status': request.GET.get('track_status'),
                    'type': request.GET.get('type'),
                    'search': request.GET.get('search', '')
                }})

            user = getattr(request, 'user', None)
            has_access = False
            if user and getattr(user, 'is_authenticated', False):
                if getattr(user, 'role', '') == 'super_admin':
                    has_access = True
                else:
                    has_access = DomainAccess.objects.filter(user=user, domain_id=domain_id).exists()
            if not has_access:
                return Response({'error': 'Forbidden: no access to this domain.'}, status=status.HTTP_403_FORBIDDEN)

            # Get prompts scoped to domain
            prompts = Prompt.objects.filter(domain_id=domain_id)
            
            # Apply filters
            group_id = request.GET.get('group_id')
            if group_id:
                prompts = prompts.filter(group_id=group_id)
            
            track_status = request.GET.get('track_status')
            if track_status:
                prompts = prompts.filter(track_status=track_status)
            
            prompt_type = request.GET.get('type')
            if prompt_type:
                prompts = prompts.filter(type=prompt_type)
            
            # Apply search filter
            search_query = request.GET.get('search', '')
            if search_query:
                prompts = prompts.filter(prompt__icontains=search_query)
            
            # Order by creation date
            prompts = prompts.order_by('-created_at')

            # Pagination
            try:
                limit = int(request.GET.get('limit', 20))
                offset = int(request.GET.get('offset', 0))
            except ValueError:
                limit = 20
                offset = 0
            limit = max(1, min(limit, 100))
            offset = max(0, offset)
            total_count = prompts.count()
            prompts = prompts[offset:offset + limit]
            
            # Prepare response data
            prompts_data = []
            for prompt in prompts:
                # Get analytics for this prompt
                analytics = PromptAnalytics.objects.filter(
                    prompt=prompt
                )
                
                prompts_data.append({
                    'id': prompt.id,
                    'prompt_text': prompt.prompt,
                    'group_id': prompt.group.group_id if prompt.group else None,
                    'group_name': f"Group {prompt.group.group_id}" if prompt.group else "No Group",
                    'domain_id': prompt.domain.id,
                    'domain_name': prompt.domain.name,
                    'track_status': prompt.track_status,
                    'type': prompt.type,
                    'last_tracked_at': prompt.tracked_at.isoformat() if prompt.tracked_at else None,
                    'track_message': prompt.track_message,
                    'created_at': prompt.created_at.isoformat(),
                    'modified_at': prompt.modified_at.isoformat(),
                    'analytics_summary': {
                        'total_analytics': analytics.count(),
                        'mentions_count': analytics.filter(is_mention=True, is_published=True).count(),
                        'avg_position': float(analytics.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0),
                        'platforms': list(analytics.values_list('platform', flat=True).distinct()),
                        'latest_mention': analytics.filter(is_mention=True, is_published=True).order_by('-created_at').first().created_at.isoformat() if analytics.filter(is_mention=True, is_published=True).exists() else None
                    }
                })
            
            return Response({
                'prompts': prompts_data,
                'total_count': total_count,
                'filters_applied': {
                    'group_id': group_id,
                    'domain_id': domain_id,
                    'track_status': track_status,
                    'type': prompt_type,
                    'search': search_query
                },
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'returned': len(prompts_data)
                }
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve prompts: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        try:
            # Validate required fields
            prompt_text = request.data.get('prompt')
            domain_id = request.data.get('domain_id')
            
            if not prompt_text or not domain_id:
                return Response(
                    {'error': 'prompt and domain_id are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get optional fields
            group_id = request.data.get('group_id')
            track_status = request.data.get('track_status', 'active')
            prompt_type = request.data.get('type', 'primary')
            track_message = request.data.get('track_message', '')
            
            # Create new prompt (attach organisation from domain)
            domain = get_object_or_404(Domain, id=domain_id)
            prompt = Prompt.objects.create(
                prompt=prompt_text,
                group_id=group_id,
                domain=domain,
                organisation=domain.organisation,
                track_status=track_status,
                type=prompt_type,
                track_message=track_message
            )
            
            return Response({
                'message': 'Prompt created successfully',
                'prompt': {
                    'id': prompt.id,
                    'prompt_text': prompt.prompt,
                    'group_id': prompt.group.group_id if prompt.group else None,
                    'domain_id': prompt.domain.id,
                    'domain_name': prompt.domain.name,
                    'track_status': prompt.track_status,
                    'type': prompt.type,
                    'created_at': prompt.created_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create prompt: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def prompt_detail(request, prompt_id):
    """
    Get, update, or delete a specific prompt
    """
    try:
        prompt = get_object_or_404(Prompt, id=prompt_id)
        
        if request.method == 'GET':
            # Get detailed information about the prompt
            analytics = PromptAnalytics.objects.filter(
                prompt=prompt
            ).order_by('-created_at')
            
            analytics_data = []
            for analytic in analytics:
                analytics_data.append({
                    'id': analytic.id,
                    'platform': analytic.platform,
                    'is_mention': analytic.is_mention,
                    'total_mentions': analytic.total_mentions,
                    'total_citations': analytic.total_citations,
                    'position': float(analytic.position),
                    'sentiment': analytic.sentiment,
                    'sentiment_score': float(analytic.sentiment_score),
                    'context_summary': analytic.context_summary,
                    'views': analytic.views,
                    'shares': analytic.shares,
                    'engagement_score': float(analytic.engagement_score),
                    'created_at': analytic.created_at.isoformat(),
                    'citations_count': len(analytic.citations) if analytic.citations else 0
                })
            
            return Response({
                'prompt': {
                    'id': prompt.id,
                    'prompt_text': prompt.prompt,
                    'group_id': prompt.group.group_id if prompt.group else None,
                    'group_name': f"Group {prompt.group.group_id}" if prompt.group else "No Group",
                    'domain_id': prompt.domain.id,
                    'domain_name': prompt.domain.name,
                    'track_status': prompt.track_status,
                    'type': prompt.type,
                    'last_tracked_at': prompt.tracked_at.isoformat() if prompt.tracked_at else None,
                    'track_message': prompt.track_message,
                    'created_at': prompt.created_at.isoformat(),
                    'modified_at': prompt.modified_at.isoformat(),
                    'analytics': analytics_data,
                    'analytics_summary': {
                        'total_analytics': analytics.count(),
                        'mentions_count': analytics.filter(is_mention=True, is_published=True).count(),
                        'platforms': list(analytics.values_list('platform', flat=True).distinct()),
                        'avg_position': float(analytics.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0),
                        'avg_sentiment': float(analytics.aggregate(avg_sent=Avg('sentiment_score'))['avg_sent'] or 0)
                    }
                }
            })
        
        elif request.method == 'PUT':
            # Update prompt information
            prompt.prompt = request.data.get('prompt', prompt.prompt)
            prompt.group_id = request.data.get('group_id', prompt.group_id)
            prompt.track_status = request.data.get('track_status', prompt.track_status)
            prompt.type = request.data.get('type', prompt.type)
            prompt.track_message = request.data.get('track_message', prompt.track_message)
            prompt.save()
            
            return Response({
                'message': 'Prompt updated successfully',
                'prompt': {
                    'id': prompt.id,
                    'prompt_text': prompt.prompt,
                    'group_id': prompt.group.group_id if prompt.group else None,
                    'track_status': prompt.track_status,
                    'type': prompt.type,
                    'modified_at': prompt.modified_at.isoformat()
                }
            })
        
        elif request.method == 'DELETE':
            # Delete the prompt (this will cascade delete all analytics)
            prompt.delete()
            return Response({
                'message': 'Prompt deleted successfully'
            })
            
    except Exception as e:
        return Response(
            {'error': f'Failed to process prompt: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_update_prompts(request):
    """
    Bulk update prompts (track status, type, etc.)
    """
    try:
        prompt_ids = request.data.get('prompt_ids', [])
        updates = request.data.get('updates', {})
        
        if not prompt_ids:
            return Response(
                {'error': 'prompt_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate updates
        allowed_updates = ['track_status', 'type', 'track_message', 'group_id']
        for key in updates.keys():
            if key not in allowed_updates:
                return Response(
                    {'error': f'Invalid update field: {key}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update prompts
        updated_count = 0
        for prompt_id in prompt_ids:
            try:
                prompt = Prompt.objects.get(id=prompt_id)
                for key, value in updates.items():
                    setattr(prompt, key, value)
                prompt.save()
                updated_count += 1
            except Prompt.DoesNotExist:
                continue
        
        return Response({
            'message': f'Successfully updated {updated_count} prompts',
            'updated_count': updated_count,
            'total_requested': len(prompt_ids)
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to bulk update prompts: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # Temporarily allow all for testing
def prompt_analytics(request, prompt_id):
    """
    Get analytics for a specific prompt
    """
    try:
        prompt = get_object_or_404(Prompt, id=prompt_id)
        
        # Get analytics for this prompt
        analytics = PromptAnalytics.objects.filter(
            prompt=prompt
        ).order_by('-created_at')
        
        # Apply filters
        platform = request.GET.get('platform')
        if platform:
            analytics = analytics.filter(platform=platform)
        
        is_mention = request.GET.get('is_mention')
        if is_mention is not None:
            analytics = analytics.filter(is_mention=is_mention.lower() == 'true')
        
        # Prepare response data
        analytics_data = []
        for analytic in analytics:
            citations_data = []
            if analytic.citations:
                for i, citation in enumerate(analytic.citations):
                    citations_data.append({
                        'id': i + 1,
                        'text': citation.get('text', ''),
                        'source': citation.get('source', ''),
                        'url': citation.get('url', ''),
                        'description': citation.get('description', '')
                    })
            
            analytics_data.append({
                'id': analytic.id,
                'platform': analytic.platform,
                'is_mention': analytic.is_mention,
                'total_mentions': analytic.total_mentions,
                'total_citations': analytic.total_citations,
                'position': float(analytic.position),
                'sentiment': analytic.sentiment,
                'sentiment_score': float(analytic.sentiment_score),
                'context_summary': analytic.context_summary,
                'views': analytic.views,
                'shares': analytic.shares,
                'engagement_score': float(analytic.engagement_score),
                'competitor_mentions': analytic.competitor_mentions,
                'key_topics': analytic.key_topics,
                'created_at': analytic.created_at.isoformat(),
                'citations': citations_data,
                'citations_count': len(citations_data)
            })
        
        return Response({
            'prompt': {
                'id': prompt.id,
                'prompt_text': prompt.prompt,
                'group_id': prompt.group.group_id if prompt.group else None,
                'domain_name': prompt.domain.name
            },
            'analytics': analytics_data,
            'total_count': len(analytics_data),
            'filters_applied': {
                'platform': platform,
                'is_mention': is_mention
            },
            'summary': {
                'total_analytics': analytics.count(),
                'mentions_count': analytics.filter(is_mention=True, is_published=True).count(),
                'platforms': list(analytics.values_list('platform', flat=True).distinct()),
                'avg_position': float(analytics.aggregate(avg_pos=Avg('position'))['avg_pos'] or 0),
                'avg_sentiment': float(analytics.aggregate(avg_sent=Avg('sentiment_score'))['avg_sent'] or 0)
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve prompt analytics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

