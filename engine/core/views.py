from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from shared_models.models import Domain, Prompt, PromptAnalytics, PromptGroup
from .domain_processor import DomainProcessor
from .processing_tasks import process_domain_task, process_prompt_analytics_task
from .serializers import DomainSerializer, ProcessingStatusSerializer
from django.db.models import Avg, Count, Q
from .prompt_analytics_processor import PromptAnalyticsProcessor


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
            'INIT': Domain.objects.filter(track_status='INIT').count(),
            'SCHD': Domain.objects.filter(track_status='SCHD').count(),
            'PROC': Domain.objects.filter(track_status='PROC').count(),
            'COMP': Domain.objects.filter(track_status='COMP').count(),
            'FAIL': Domain.objects.filter(track_status='FAIL').count(),
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
        sync = bool(request.data.get('sync'))  # if true, run inline without Celery
        if not domain_id:
            return Response({
                'success': False,
                'error': 'domain_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if domain exists
        domain = get_object_or_404(Domain, id=domain_id)
        
        # If sync requested, process inline without Celery
        if sync:
            if domain.track_status == 'PROC':
                return Response({
                    'success': False,
                    'error': 'Domain is already being processed'
                }, status=status.HTTP_409_CONFLICT)

            # Mark as processing and run inline
            domain.track_status = 'PROC'
            domain.track_message = 'Processing inline via /api/start (sync)'
            domain.save(update_fields=['track_status', 'track_message', 'modified_at'])

            try:
                # Execute synchronously
                domain_processor._process_single_domain(domain.id)
                # Success
                domain.track_status = 'COMP'
                domain.track_message = 'Completed inline processing'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                return Response({
                    'success': True,
                    'message': f'Completed inline processing for domain: {domain.name}',
                    'domain_id': domain_id,
                    'mode': 'sync'
                })
            except Exception as inline_err:
                domain.track_status = 'FAIL'
                domain.track_message = f'Inline processing failed: {inline_err}'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                return Response({
                    'success': False,
                    'error': f'Inline processing failed: {inline_err}',
                    'domain_id': domain_id,
                    'mode': 'sync'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Default: enqueue Celery task (idempotent scheduling)
        if domain.track_status in ['PROC']:
            return Response({
                'success': False,
                'error': 'Domain is already being processed'
            }, status=status.HTTP_409_CONFLICT)

        if domain.track_status == 'INIT':
            domain.track_status = 'SCHD'
            domain.track_message = 'Scheduled via API request'
            domain.save(update_fields=['track_status', 'track_message', 'modified_at'])

        process_domain_task.delay(domain_id)

        return Response({
            'success': True,
            'message': f'Started processing for domain: {domain.name}',
            'domain_id': domain_id,
            'mode': 'async'
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
            domains = Domain.objects.filter(track_status=status_filter)
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
        if domain.track_status != 'INIT':
            return Response({
                'success': False,
                'error': f'Domain is in {domain.track_status} status. Only INIT domains can be scheduled.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        domain.track_status = 'SCHD'
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
        domain.track_status = 'INIT'
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
            'INIT': prompts.filter(track_status='INIT').count(),
            'SCHD': prompts.filter(track_status='SCHD').count(),
            'PROC': prompts.filter(track_status='PROC').count(),
            'COMP': prompts.filter(track_status='COMP').count(),
            'FAIL': prompts.filter(track_status='FAIL').count(),
        }
        
        # Get analytics processing statistics
        analytics = PromptAnalytics.objects.filter(prompt__domain=domain)
        total_analytics = analytics.count()
        
        # Derive platform status using platform field and track_status
        platform_status = {}
        platform_map = {
            'chatgpt': 'ChatGPT',
            'gemini': 'Google Gemini',
            'perplexity': 'Perplexity',
        }
        for key, label in platform_map.items():
            platform_status[key] = {
                'pending': analytics.filter(platform=label, track_status='INIT').count(),
                'processing': analytics.filter(platform=label, track_status='PROC').count(),
                'completed': analytics.filter(platform=label, track_status='COMP').count(),
                'failed': analytics.filter(platform=label, track_status='FAIL').count(),
            }
        
        # Calculate overall progress
        # Each prompt can have up to 3 analytics rows (one per platform)
        total_platform_tasks = (
            analytics.filter(platform='ChatGPT').count() +
            analytics.filter(platform='Google Gemini').count() +
            analytics.filter(platform='Perplexity').count()
        ) or (total_prompts * 3)
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
                    'track_status': domain.track_status
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

@api_view(['POST'])
@permission_classes([AllowAny])
def start_single_prompt_processing(request):
    """Start analytics processing for a single prompt"""
    try:
        prompt_id = request.data.get('prompt_id')
        if not prompt_id:
            return Response({'error': 'prompt_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if prompt exists
        prompt = get_object_or_404(Prompt, id=prompt_id)
        
        # Queue the task
        task = process_prompt_analytics_task.delay(prompt_id)
        
        return Response({
            'message': 'Single prompt analytics processing started',
            'task_id': task.id,
            'prompt_id': prompt_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_prompt_processing(request):
    """Start processing for a specific prompt (sync or async)."""
    try:
        prompt_id = request.data.get('prompt_id')
        sync = bool(request.data.get('sync'))
        if not prompt_id:
            return Response({
                'success': False,
                'error': 'prompt_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ensure prompt exists
        prompt = get_object_or_404(Prompt, id=prompt_id)

        if sync:
            # Run inline without Celery
            processor = PromptAnalyticsProcessor(max_concurrent_prompts=10)
            result = processor.process_single_prompt(int(prompt_id))
            ok = 'error' not in result
            return Response({
                'success': ok,
                'mode': 'sync',
                **result
            }, status=status.HTTP_200_OK if ok else status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Default: enqueue via Celery
        task = process_prompt_analytics_task.delay(int(prompt_id))
        return Response({
            'success': True,
            'mode': 'async',
            'task_id': task.id,
            'prompt_id': int(prompt_id)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
