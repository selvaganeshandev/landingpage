from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from shared_models.models import Domain, Prompt, PromptAnalytics, PromptGroup
from .domain_processor import DomainProcessor
from .tasks import process_domain_task, process_prompt_analytics_task
from .serializers import DomainSerializer, ProcessingStatusSerializer
from django.db.models import Avg, Count, Q


# Global domain processor instance
domain_processor = DomainProcessor()


@api_view(['GET'])
@permission_classes([AllowAny])
def processing_status(request):
    """
    Get current processing status
    """
    try:
        status_data = domain_processor.get_processing_status()
        
        # Get domain counts by status
        domain_counts = {
            'INIT': Domain.objects.filter(processing_status='INIT').count(),
            'SCHD': Domain.objects.filter(processing_status='SCHD').count(),
            'PROC': Domain.objects.filter(processing_status='PROC').count(),
            'COMP': Domain.objects.filter(processing_status='COMP').count(),
            'FAIL': Domain.objects.filter(processing_status='FAIL').count(),
        }
        
        status_data['domain_counts'] = domain_counts
        
        return Response({
            'success': True,
            'data': status_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_processing(request):
    """
    Start processing for a specific domain
    """
    try:
        domain_id = request.data.get('domain_id')
        if not domain_id:
            return Response({
                'success': False,
                'error': 'domain_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if domain exists
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Enqueue Celery task (idempotent scheduling)
        if domain.processing_status in ['PROC']:
            return Response({
                'success': False,
                'error': 'Domain is already being processed'
            }, status=status.HTTP_409_CONFLICT)

        if domain.processing_status == 'INIT':
            domain.processing_status = 'SCHD'
            domain.track_status = 'Scheduled'
            domain.track_message = 'Scheduled via API request'
            domain.save(update_fields=['processing_status', 'track_status', 'track_message', 'modified_at'])

        process_domain_task.delay(domain_id)

        return Response({
            'success': True,
            'message': f'Started processing for domain: {domain.name}',
            'domain_id': domain_id
        })
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def domain_list(request):
    """
    Get list of domains with their processing status
    """
    try:
        status_filter = request.GET.get('status')
        
        if status_filter:
            domains = Domain.objects.filter(processing_status=status_filter)
        else:
            domains = Domain.objects.all()
        
        serializer = DomainSerializer(domains, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': domains.count()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def domain_detail(request, domain_id):
    """
    Get detailed information about a specific domain
    """
    try:
        domain = get_object_or_404(Domain, id=domain_id)
        serializer = DomainSerializer(domain)
        
        # Get additional statistics
        stats = {
            'keywords_count': domain.keywords.count(),
            'prompt_groups_count': domain.prompt_groups.count(),
            'prompts_count': domain.prompts.count(),
            'analytics_count': domain.prompt_analytics.count()
        }
        
        return Response({
            'success': True,
            'data': {
                'domain': serializer.data,
                'statistics': stats
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def schedule_domain(request):
    """
    Schedule a domain for processing (set status to SCHD)
    """
    try:
        domain_id = request.data.get('domain_id')
        if not domain_id:
            return Response({
                'success': False,
                'error': 'domain_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Only schedule if domain is in INIT status
        if domain.processing_status != 'INIT':
            return Response({
                'success': False,
                'error': f'Domain is in {domain.processing_status} status. Only INIT domains can be scheduled.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        domain.processing_status = 'SCHD'
        domain.track_status = 'Scheduled'
        domain.track_message = 'Scheduled for processing'
        domain.save()
        
        return Response({
            'success': True,
            'message': f'Domain {domain.name} scheduled for processing',
            'domain_id': domain_id
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_domain(request):
    """
    Reset a domain to INIT status for reprocessing
    """
    try:
        domain_id = request.data.get('domain_id')
        if not domain_id:
            return Response({
                'success': False,
                'error': 'domain_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Reset domain status
        domain.processing_status = 'INIT'
        domain.track_status = 'Initial'
        domain.track_message = 'Reset for processing'
        domain.save()
        
        return Response({
            'success': True,
            'message': f'Domain {domain.name} reset to INIT status',
            'domain_id': domain_id
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_prompt_analytics_processing(request):
    """
    Start prompt analytics processing for a specific domain
    """
    try:
        domain_id = request.data.get('domain_id')
        if not domain_id:
            return Response({
                'success': False,
                'error': 'domain_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if domain exists
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Check if domain has prompts
        prompts_count = domain.prompts.count()
        if prompts_count == 0:
            return Response({
                'success': False,
                'error': 'Domain has no prompts to process'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Enqueue Celery task for prompt analytics processing
        process_prompt_analytics_task.delay(domain_id)
        
        return Response({
            'success': True,
            'message': f'Started prompt analytics processing for domain: {domain.name}',
            'domain_id': domain_id,
            'prompts_count': prompts_count
        })
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def prompt_analytics_status(request, domain_id):
    """
    Get prompt analytics processing status for a domain
    """
    try:
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Get prompt processing statistics
        prompts = domain.prompts.all()
        total_prompts = prompts.count()
        
        status_counts = {
            'pending': prompts.filter(processing_status='pending').count(),
            'processing': prompts.filter(processing_status='processing').count(),
            'completed': prompts.filter(processing_status='completed').count(),
            'failed': prompts.filter(processing_status='failed').count(),
        }
        
        # Get analytics processing statistics
        analytics = PromptAnalytics.objects.filter(prompt__domain=domain)
        total_analytics = analytics.count()
        
        platform_status = {
            'chatgpt': {
                'pending': analytics.filter(chatgpt_status='pending').count(),
                'processing': analytics.filter(chatgpt_status='processing').count(),
                'completed': analytics.filter(chatgpt_status='completed').count(),
                'failed': analytics.filter(chatgpt_status='failed').count(),
            },
            'gemini': {
                'pending': analytics.filter(gemini_status='pending').count(),
                'processing': analytics.filter(gemini_status='processing').count(),
                'completed': analytics.filter(gemini_status='completed').count(),
                'failed': analytics.filter(gemini_status='failed').count(),
            },
            'perplexity': {
                'pending': analytics.filter(perplexity_status='pending').count(),
                'processing': analytics.filter(perplexity_status='processing').count(),
                'completed': analytics.filter(perplexity_status='completed').count(),
                'failed': analytics.filter(perplexity_status='failed').count(),
            }
        }
        
        # Calculate overall progress
        total_platform_tasks = total_analytics * 3  # 3 platforms per analytics
        completed_platform_tasks = (
            platform_status['chatgpt']['completed'] +
            platform_status['gemini']['completed'] +
            platform_status['perplexity']['completed']
        )
        
        progress_percentage = (completed_platform_tasks / total_platform_tasks * 100) if total_platform_tasks > 0 else 0
        
        return Response({
            'success': True,
            'data': {
                'domain': {
                    'id': domain.id,
                    'name': domain.name,
                    'processing_status': domain.processing_status
                },
                'prompts': {
                    'total': total_prompts,
                    'status_counts': status_counts
                },
                'analytics': {
                    'total': total_analytics,
                    'platform_status': platform_status,
                    'progress_percentage': round(progress_percentage, 2)
                }
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def prompt_analytics_summary(request, domain_id):
    """
    Get aggregated prompt analytics summary for a domain
    """
    try:
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Get aggregated analytics data
        analytics = PromptAnalytics.objects.filter(prompt__domain=domain)
        
        # Calculate aggregated metrics
        aggregated_metrics = analytics.aggregate(
            total_citations=Count('total_citations'),
            total_mentions=Count('total_mentions'),
            avg_position=Avg('position'),
            avg_sentiment_score=Avg('sentiment_score')
        )
        
        # Get metrics by platform
        platform_metrics = {}
        for platform in ['ChatGPT', 'Google Gemini', 'Perplexity']:
            platform_analytics = analytics.filter(platform=platform)
            platform_metrics[platform] = platform_analytics.aggregate(
                total_citations=Count('total_citations'),
                total_mentions=Count('total_mentions'),
                avg_position=Avg('position'),
                avg_sentiment_score=Avg('sentiment_score')
            )
        
        # Get prompt group summaries
        prompt_groups = PromptGroup.objects.filter(domain=domain)
        group_summaries = []
        
        for group in prompt_groups:
            group_analytics = analytics.filter(prompt__group=group)
            group_summary = {
                'group_id': group.group_id,
                'title': group.title,
                'prompts_count': group.prompts.count(),
                'analytics_count': group_analytics.count(),
                'metrics': group_analytics.aggregate(
                    total_citations=Count('total_citations'),
                    total_mentions=Count('total_mentions'),
                    avg_position=Avg('position'),
                    avg_sentiment_score=Avg('sentiment_score')
                )
            }
            group_summaries.append(group_summary)
        
        return Response({
            'success': True,
            'data': {
                'domain': {
                    'id': domain.id,
                    'name': domain.name
                },
                'aggregated_metrics': aggregated_metrics,
                'platform_metrics': platform_metrics,
                'group_summaries': group_summaries
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)