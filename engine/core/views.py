from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from django.db import transaction
from django.conf import settings
import logging
from shared_models.models import (
    Domain, Prompt, PromptAnalytics, PromptGroup,
    Competitor, CompetitorPromptAnalytics, CompetitorAnalytics, ShareOfVoiceAnalytics
)
from .domain_processor import DomainProcessor
from .processing_tasks import process_domain_task, process_prompt_analytics_task, process_single_competitor_task
from .serializers import (
    DomainSerializer, ProcessingStatusSerializer,
    CompetitorSerializer, CompetitorPromptAnalyticsSerializer,
    CompetitorAnalyticsSerializer, ShareOfVoiceAnalyticsSerializer
)
from django.db.models import Avg, Count, Q, Sum
from .prompt_analytics_processor import PromptAnalyticsProcessor

logger = logging.getLogger(__name__)


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
            if domain.processing_status == 'PROC':
                return Response({
                    'success': False,
                    'error': 'Domain is already being processed'
                }, status=status.HTTP_409_CONFLICT)

            # Set to SCHD so processor can handle the transition to PROC
            # The processor expects SCHD status and will update it to PROC internally
            # Handle both INIT and other statuses (except PROC which is checked above)
            if domain.processing_status not in ['SCHD', 'PROC']:
                domain.processing_status = 'SCHD'
                domain.track_message = 'Scheduled for synchronous processing via /api/start'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])

            try:
                # Execute synchronously - processor will handle SCHD -> PROC transition
                domain_processor._process_single_domain(domain.id)
                # DO NOT set status to COMP here - the processor handles status updates
                # The domain will be in PROC status until analytics processing completes
                domain.refresh_from_db()  # Get latest status from processor
                return Response({
                    'success': True,
                    'message': f'Domain processing started for: {domain.name}',
                    'domain_id': domain_id,
                    'mode': 'sync',
                    'current_status': domain.processing_status,
                    'current_message': domain.track_message
                })
            except Exception as inline_err:
                domain.processing_status = 'FAIL'
                domain.track_message = f'Inline processing failed: {inline_err}'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                return Response({
                    'success': False,
                    'error': f'Inline processing failed: {inline_err}',
                    'domain_id': domain_id,
                    'mode': 'sync'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Default: enqueue Celery task (idempotent scheduling)
        if domain.processing_status in ['PROC']:
            return Response({
                'success': False,
                'error': 'Domain is already being processed'
            }, status=status.HTTP_409_CONFLICT)

        if domain.processing_status == 'INIT':
            domain.processing_status = 'SCHD'
            domain.track_message = 'Scheduled via API request'
            domain.tracked_at = timezone.now()
            domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])

        # Try to enqueue Celery task, but don't fail if Celery is not available
        # The processing loop will pick up SCHD domains anyway
        try:
            process_domain_task.delay(domain_id)
            celery_mode = 'async'
        except Exception as celery_err:
            # Celery not available - processing loop will handle it
            print(f"Celery not available, domain {domain_id} will be processed by the processing loop: {celery_err}")
            celery_mode = 'loop'

        return Response({
            'success': True,
            'message': f'Started processing for domain: {domain.name}',
            'domain_id': domain_id,
            'mode': celery_mode
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
            'prompts_count': Prompt.objects.filter(group__domain=domain).count(),
            'analytics_count': PromptAnalytics.objects.filter(prompt__group__domain=domain).count()
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
        domain.track_message = 'Scheduled for processing'
        domain.tracked_at = timezone.now()
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
        domain.track_message = 'Reset for processing'
        domain.tracked_at = timezone.now()
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
        sync_param = request.data.get('sync')
        if isinstance(sync_param, str):
            sync = sync_param.lower() in ('true', '1', 'yes')
        else:
            sync = bool(sync_param)
        
        if not domain_id:
            return Response({
                'success': False,
                'error': 'domain_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if domain exists
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Check if domain has prompts (through prompt groups)
        prompts = Prompt.objects.filter(group__domain=domain)
        prompts_count = prompts.count()
        if prompts_count == 0:
            return Response({
                'success': False,
                'error': 'Domain has no prompts to process'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if sync:
            # Process all prompts synchronously
            processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
            processed = 0
            failed = 0
            
            # Get all INIT prompts for this domain
            init_prompts = prompts.filter(track_status='INIT')
            
            for prompt in init_prompts:
                try:
                    result = processor.process_single_prompt(prompt.id)
                    if 'error' not in result:
                        processed += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing prompt {prompt.id}: {str(e)}")
            
            return Response({
                'success': True,
                'message': f'Processed prompts for domain: {domain.name}',
                'domain_id': domain_id,
                'mode': 'sync',
                'total_prompts': prompts_count,
                'processed': processed,
                'failed': failed
            })
        else:
            # Use scheduler to process prompts asynchronously (group by group)
            # The scheduler will pick up INIT prompt groups automatically
            from .processing_tasks import process_prompt_analytics_scheduler
            process_prompt_analytics_scheduler.delay()
            
            return Response({
                'success': True,
                'message': f'Started prompt analytics processing for domain: {domain.name}',
                'domain_id': domain_id,
                'mode': 'async',
                'prompts_count': prompts_count,
                'note': 'Prompts will be processed by the scheduler (group by group)'
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
        
        # Get prompt processing statistics (through prompt groups)
        prompts = Prompt.objects.filter(group__domain=domain)
        total_prompts = prompts.count()
        
        status_counts = {
            'INIT': prompts.filter(track_status='INIT').count(),
            'SCHD': prompts.filter(track_status='SCHD').count(),
            'PROC': prompts.filter(track_status='PROC').count(),
            'COMP': prompts.filter(track_status='COMP').count(),
            'FAIL': prompts.filter(track_status='FAIL').count(),
        }
        
        # Get analytics processing statistics (through prompt groups)
        analytics = PromptAnalytics.objects.filter(prompt__group__domain=domain)
        total_analytics = analytics.count()
        
        # Derive platform status using platform field and prompt track_status
        platform_status = {}
        platform_map = {
            'chatgpt': 'ChatGPT',
            'gemini': 'Google Gemini',
            'perplexity': 'Perplexity',
        }
        for key, label in platform_map.items():
            # Use prompt__track_status because PromptAnalytics.track_status is never updated
            platform_status[key] = {
                'pending': analytics.filter(platform=label, prompt__track_status='INIT').count(),
                'processing': analytics.filter(platform=label, prompt__track_status='PROC').count(),
                'completed': analytics.filter(platform=label, prompt__track_status='COMP').count(),
                'failed': analytics.filter(platform=label, prompt__track_status='FAIL').count(),
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
        
        # Get aggregated analytics data (through prompt groups)
        analytics = PromptAnalytics.objects.filter(prompt__group__domain=domain)
        
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
        # Properly handle sync parameter - can be boolean or string "true"/"false"
        sync_param = request.data.get('sync')
        if isinstance(sync_param, str):
            sync = sync_param.lower() in ('true', '1', 'yes')
        else:
            sync = bool(sync_param)
        
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


# ============================================================================
# COMPETITOR ENDPOINTS
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def competitor_list(request):
    """
    GET: List all competitors
    POST: Create a new competitor (sets track_status='INIT' automatically)
    """
    if request.method == 'GET':
        domain_id = request.query_params.get('domain_id')
        
        queryset = Competitor.objects.all()
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        
        queryset = queryset.select_related('domain').order_by('-modified_at')
        serializer = CompetitorSerializer(queryset, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = CompetitorSerializer(data=request.data)
        if serializer.is_valid():
            # Auto-set track_status to INIT when creating
            competitor = serializer.save(track_status='INIT')
            return Response(
                CompetitorSerializer(competitor).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def competitor_detail(request, competitor_id):
    """
    GET: Get competitor details
    PUT: Update competitor
    DELETE: Delete competitor
    """
    competitor = get_object_or_404(Competitor, id=competitor_id)
    
    if request.method == 'GET':
        serializer = CompetitorSerializer(competitor)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = CompetitorSerializer(competitor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        competitor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([AllowAny])
def start_single_competitor_processing(request):
    """
    Start processing for a single competitor (similar to start_single_prompt_processing).
    Takes competitor_id from request body.
    Can run synchronously (default) or asynchronously via Celery (if sync=false).
    """
    try:
        competitor_id = request.data.get('competitor_id')
        sync = request.data.get('sync', True)  # Default to sync (no Celery)
        
        if not competitor_id:
            return Response({
                'success': False,
                'error': 'competitor_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if competitor exists
        try:
            competitor = Competitor.objects.get(id=competitor_id)
        except Competitor.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Competitor with id {competitor_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if sync:
            # Run synchronously (no Celery)
            from .competitor_processor import CompetitorProcessor
            from django.conf import settings
            
            processor = CompetitorProcessor(
                max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10)
            )
            
            try:
                # Process directly (similar to process_single_competitor_task)
                with transaction.atomic():
                    comp = Competitor.objects.select_for_update().get(id=competitor_id)
                    
                    # Allow reprocessing if COMP or failed before, or if INIT
                    if comp.track_status == 'COMP':
                        comp.track_status = 'INIT'
                        comp.track_message = 'Resetting for reprocessing'
                        comp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                    elif comp.track_status not in ['INIT', 'FAIL']:
                        return Response({
                            'success': False,
                            'error': f'Competitor already in status {comp.track_status}'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Mark as SCHD
                    comp.track_status = 'SCHD'
                    comp.track_message = f"Scheduled for processing at {timezone.now()}"
                    comp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                
                # Refresh competitor from DB to ensure we have latest state
                competitor.refresh_from_db()
                
                # Link prompts to competitor
                linked_count = processor._link_prompts_to_competitor(competitor)
                
                # Mark as processing
                with transaction.atomic():
                    comp = Competitor.objects.select_for_update().get(id=competitor_id)
                    comp.track_status = 'PROC'
                    comp.track_message = "Processing competitor analytics"
                    comp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                
                # Refresh again before processing
                competitor.refresh_from_db()
                
                # Process prompts
                processor._process_competitor_prompts(competitor)
                
                # Aggregate analytics
                processor._aggregate_competitor_analytics(competitor)
                
                # Mark as complete
                with transaction.atomic():
                    comp = Competitor.objects.select_for_update().get(id=competitor_id)
                    comp.track_status = 'COMP'
                    comp.track_message = f"Completed at {timezone.now()}"
                    comp.tracked_at = timezone.now()
                    comp.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                
                # Refresh competitor object
                competitor.refresh_from_db()
                
                return Response({
                    'success': True,
                    'message': f'Single competitor processing completed for {competitor.name}',
                    'mode': 'sync',
                    'competitor_id': competitor_id,
                    'competitor_name': competitor.name,
                    'track_status': competitor.track_status,
                    'prompts_linked': linked_count,
                    'total_mentions': competitor.total_mentions,
                    'visibility_score': str(competitor.visibility_score),
                    'share_of_voice_percentage': str(competitor.share_of_voice_percentage)
                }, status=status.HTTP_200_OK)
                
            except Exception as processing_error:
                # Mark as failed
                try:
                    with transaction.atomic():
                        comp = Competitor.objects.select_for_update().get(id=competitor_id)
                        comp.track_status = 'FAIL'
                        comp.track_message = f"Processing failed: {str(processing_error)}"
                        comp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                except:
                    pass
                
                return Response({
                    'success': False,
                    'error': str(processing_error),
                    'mode': 'sync'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Run asynchronously via Celery
            task = process_single_competitor_task.delay(competitor_id)
            
            return Response({
                'success': True,
                'message': f'Single competitor processing started for {competitor.name}',
                'mode': 'async',
                'task_id': task.id,
                'competitor_id': competitor_id,
                'competitor_name': competitor.name,
                'track_status': competitor.track_status
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def competitor_process(request, competitor_id):
    """
    Trigger processing for a specific competitor (URL parameter version)
    """
    competitor = get_object_or_404(Competitor, id=competitor_id)
    
    try:
        # Trigger the Celery task
        task = process_single_competitor_task.delay(competitor.id)
        
        return Response({
            'success': True,
            'message': f'Processing started for competitor {competitor.name}',
            'competitor_id': competitor.id,
            'track_status': competitor.track_status,
            'task_id': task.id
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def competitor_analytics(request, competitor_id):
    """
    Get detailed analytics for a competitor
    """
    competitor = get_object_or_404(Competitor, id=competitor_id)
    
    # Get competitor-prompt analytics
    prompt_analytics = CompetitorPromptAnalytics.objects.filter(
        competitor=competitor
    ).select_related('prompt')
    
    # Calculate statistics
    stats = prompt_analytics.aggregate(
        total_tested=Count('id'),
        total_mentioned=Count('id', filter=Q(is_mentioned=True)),
        avg_position=Avg('position'),
        avg_sentiment=Avg('sentiment_score'),
        total_mentions=Sum('mention_count')
    )
    
    mention_rate = 0
    if stats['total_tested'] and stats['total_tested'] > 0:
        mention_rate = (stats['total_mentioned'] / stats['total_tested']) * 100
    
    return Response({
        'competitor': CompetitorSerializer(competitor).data,
        'statistics': {
            'total_prompts_tested': stats['total_tested'] or 0,
            'times_mentioned': stats['total_mentioned'] or 0,
            'mention_rate': round(mention_rate, 2),
            'average_position': round(float(stats['avg_position'] or 0), 2),
            'average_sentiment': round(float(stats['avg_sentiment'] or 0), 2),
            'total_mention_count': stats['total_mentions'] or 0,
        },
        'recent_prompts': CompetitorPromptAnalyticsSerializer(
            prompt_analytics.order_by('-tracked_at')[:10], many=True
        ).data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def competitor_prompt_analytics_list(request):
    """
    List competitor-prompt analytics
    """
    competitor_id = request.query_params.get('competitor_id')
    domain_id = request.query_params.get('domain_id')
    
    queryset = CompetitorPromptAnalytics.objects.all()
    
    if competitor_id:
        queryset = queryset.filter(competitor_id=competitor_id)
    
    if domain_id:
        queryset = queryset.filter(competitor__domain_id=domain_id)
    
    queryset = queryset.select_related('competitor', 'prompt').order_by('-tracked_at')
    serializer = CompetitorPromptAnalyticsSerializer(queryset[:100], many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def competitor_gaps(request):
    """
    Find opportunity gaps - prompts where competitor appears in top positions
    """
    domain_id = request.query_params.get('domain_id')
    competitor_id = request.query_params.get('competitor_id')
    
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    queryset = CompetitorPromptAnalytics.objects.filter(
        competitor__domain_id=domain_id,
        is_mentioned=True,  # Competitor is mentioned
        position__lte=5  # In top 5
    ).select_related('competitor', 'prompt')
    
    if competitor_id:
        queryset = queryset.filter(competitor_id=competitor_id)
    
    queryset = queryset.order_by('position')
    serializer = CompetitorPromptAnalyticsSerializer(queryset[:50], many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def share_of_voice(request):
    """
    Get Share of Voice analytics for a domain
    """
    domain_id = request.query_params.get('domain_id')
    
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get latest timestamp
    latest = ShareOfVoiceAnalytics.objects.filter(
        domain_id=domain_id
    ).order_by('-timestamp').first()
    
    if not latest:
        return Response({
            'domain_id': int(domain_id),
            'message': 'No share of voice data available yet',
            'players': []
        })
    
    # Get all records for latest timestamp
    sov_data = ShareOfVoiceAnalytics.objects.filter(
        domain_id=domain_id,
        timestamp=latest.timestamp
    ).select_related('competitor', 'domain').order_by('market_position')
    
    serializer = ShareOfVoiceAnalyticsSerializer(sov_data, many=True)
    
    return Response({
        'domain_id': int(domain_id),
        'timestamp': latest.timestamp,
        'platform': latest.platform or 'Overall',
        'players': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def competitor_analytics_trends(request):
    """
    Get time-series trends for competitor analytics
    """
    competitor_id = request.query_params.get('competitor_id')
    days = int(request.query_params.get('days', 30))
    
    if not competitor_id:
        return Response(
            {'error': 'competitor_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from datetime import timedelta
    start_date = timezone.now().date() - timedelta(days=days)
    
    analytics = CompetitorAnalytics.objects.filter(
        competitor_id=competitor_id,
        timestamp__gte=start_date
    ).order_by('timestamp')
    
    serializer = CompetitorAnalyticsSerializer(analytics, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_track_status(request):
    """
    Reset track_status for domains, prompt groups, or prompts to INIT.
    Useful for testing and reprocessing.
    
    Request body:
    {
        "entity_type": "domain" | "prompt_group" | "prompt",
        "entity_id": <id>,
        "reset_to": "INIT" (default) | "SCHD" | "PROC"
    }
    """
    try:
        import json
        
        data = json.loads(request.body)
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')
        reset_to = data.get('reset_to', 'INIT')
        
        if not entity_type or not entity_id:
            return Response({
                "status": "error",
                "message": "entity_type and entity_id are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if reset_to not in ['INIT', 'SCHD', 'PROC']:
            return Response({
                "status": "error",
                "message": "reset_to must be INIT, SCHD, or PROC"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if entity_type == 'domain':
            try:
                entity = Domain.objects.get(id=entity_id)
                entity.processing_status = reset_to
                entity.track_message = f"Reset to {reset_to} via API"
                entity.tracked_at = timezone.now()
                entity.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                
                return Response({
                    "status": "success",
                    "message": f"Domain {entity_id} reset to {reset_to}",
                    "entity_type": "domain",
                    "entity_id": entity_id,
                    "new_status": reset_to
                })
            except Domain.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": f"Domain with id {entity_id} not found"
                }, status=status.HTTP_404_NOT_FOUND)
        
        elif entity_type == 'prompt_group':
            try:
                entity = PromptGroup.objects.get(id=entity_id)
                entity.track_status = reset_to
                entity.track_message = f"Reset to {reset_to} via API"
                entity.tracked_at = timezone.now()
                entity.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                
                return Response({
                    "status": "success",
                    "message": f"PromptGroup {entity_id} reset to {reset_to}",
                    "entity_type": "prompt_group",
                    "entity_id": entity_id,
                    "new_status": reset_to
                })
            except PromptGroup.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": f"PromptGroup with id {entity_id} not found"
                }, status=status.HTTP_404_NOT_FOUND)
        
        elif entity_type == 'prompt':
            try:
                entity = Prompt.objects.get(id=entity_id)
                entity.track_status = reset_to
                entity.track_message = f"Reset to {reset_to} via API"
                entity.tracked_at = timezone.now()
                entity.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                
                return Response({
                    "status": "success",
                    "message": f"Prompt {entity_id} reset to {reset_to}",
                    "entity_type": "prompt",
                    "entity_id": entity_id,
                    "new_status": reset_to
                })
            except Prompt.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": f"Prompt with id {entity_id} not found"
                }, status=status.HTTP_404_NOT_FOUND)
        
        else:
            return Response({
                "status": "error",
                "message": f"Invalid entity_type: {entity_type}. Must be 'domain', 'prompt_group', or 'prompt'"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except json.JSONDecodeError:
        return Response({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error resetting track_status: {str(e)}")
        return Response({
            "status": "error",
            "message": f"Error resetting track_status: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
