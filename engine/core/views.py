from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from django.shortcuts import get_object_or_404
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.conf import settings
import logging
from shared_models.models import (
    Domain, Prompt, PromptAnalytics, PromptGroup,
    Competitor, CompetitorPromptAnalytics, CompetitorAnalytics, ShareOfVoiceAnalytics,
    Topic, TopicKeyword, KeywordAnalytics, TopicAnalytics
)
from .domain_processor import DomainProcessor
from .processing_tasks import process_domain_task, process_prompt_analytics_task, process_single_competitor_task, process_topics_for_domain_task, process_misinformation_scan_task
from .serializers import (
    DomainSerializer, ProcessingStatusSerializer,
    CompetitorSerializer, CompetitorPromptAnalyticsSerializer,
    CompetitorAnalyticsSerializer, ShareOfVoiceAnalyticsSerializer
)
from django.db.models import Avg, Count, Q, Sum, Max, Min
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
            'claude': 'Claude',
            'grok': 'Grok',
            'deepseek': 'DeepSeek',
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
        # Each prompt can have up to len(platform_map) analytics rows (one per platform)
        total_platform_tasks = sum(
            analytics.filter(platform=label).count() for label in platform_map.values()
        ) or (total_prompts * len(platform_map))
        completed_platform_tasks = sum(
            platform_status[key]['completed'] for key in platform_map.keys()
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
        for platform in ['ChatGPT', 'Google Gemini', 'Perplexity', 'Claude', 'Grok', 'DeepSeek']:
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


@api_view(['POST'])
@permission_classes([AllowAny])
def start_topic_processing(request):
    """
    Start topic processing for a specific domain (sync or async).
    This manually triggers topic processing, which normally happens automatically when domain completes.
    
    Body:
        - domain_id (required): ID of domain to process topics for
        - sync (optional, default=False): If true, run synchronously without Celery
    """
    try:
        domain_id = request.data.get('domain_id')
        # Properly handle sync parameter - can be boolean or string "true"/"false"
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

        # Ensure domain exists
        domain = get_object_or_404(Domain, id=domain_id)

        if sync:
            # Run inline without Celery
            from core.topic_processor import TopicProcessor
            from core.topic_analytics_processor import TopicAnalyticsProcessor
            
            # Step 1: Group keywords into topics
            logger.info(f"Starting topic processing (sync) for domain {domain_id}")
            topic_processor = TopicProcessor()
            result = topic_processor.process_topics_for_domain(domain)
            
            if not result.get('success'):
                return Response({
                    'success': False,
                    'mode': 'sync',
                    'error': result.get('message', 'Topic processing failed')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Step 2: Process topic analytics
            logger.info(f"Starting topic analytics processing (sync) for domain {domain_id}")
            analytics_processor = TopicAnalyticsProcessor()
            analytics_result = analytics_processor.process_analytics_for_domain(domain)
            
            if not analytics_result.get('success'):
                return Response({
                    'success': False,
                    'mode': 'sync',
                    'error': analytics_result.get('message', 'Topic analytics processing failed'),
                    'topics_created': result.get('topics_created', 0)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'success': True,
                'mode': 'sync',
                'domain_id': int(domain_id),
                'topics_created': result.get('topics_created', 0),
                'keywords_processed': analytics_result.get('keywords_processed', 0),
                'topics_processed': analytics_result.get('topics_processed', 0)
            }, status=status.HTTP_200_OK)

        # Default: enqueue via Celery
        task = process_topics_for_domain_task.delay(int(domain_id))
        return Response({
            'success': True,
            'mode': 'async',
            'task_id': task.id,
            'domain_id': int(domain_id),
            'message': 'Topic processing scheduled'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in start_topic_processing: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def topic_analytics_status(request, domain_id):
    """
    Get topic analytics processing status for a domain
    """
    try:
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Get topic processing statistics
        topics = Topic.objects.filter(domain=domain)
        total_topics = topics.count()
        
        status_counts = {
            'INIT': topics.filter(track_status='INIT').count(),
            'SCHD': topics.filter(track_status='SCHD').count(),
            'PROC': topics.filter(track_status='PROC').count(),
            'COMP': topics.filter(track_status='COMP').count(),
            'FAIL': topics.filter(track_status='FAIL').count(),
        }
        
        # Get topic keyword processing statistics
        topic_keywords = TopicKeyword.objects.filter(topic__domain=domain)
        total_topic_keywords = topic_keywords.count()
        
        keyword_status_counts = {
            'INIT': topic_keywords.filter(track_status='INIT').count(),
            'COMP': topic_keywords.filter(track_status='COMP').count(),
        }
        
        # Get keyword analytics statistics
        keyword_analytics = KeywordAnalytics.objects.filter(keyword__domain=domain)
        total_keyword_analytics = keyword_analytics.count()
        
        # Get platform-wise keyword analytics status
        platform_status = {}
        for platform in ['ChatGPT', 'Google Gemini', 'Perplexity', 'Claude', 'Grok', 'DeepSeek']:
            platform_analytics = keyword_analytics.filter(platform=platform)
            platform_status[platform.lower().replace(' ', '_')] = {
                'total': platform_analytics.count(),
                'completed': platform_analytics.filter(track_status='COMP').count(),
                'processing': platform_analytics.filter(track_status='PROC').count(),
                'failed': platform_analytics.filter(track_status='FAIL').count(),
            }
        
        # Calculate overall progress
        completed_topics = status_counts['COMP']
        completed_keywords = keyword_status_counts['COMP']
        progress_percentage = (
            (completed_topics / total_topics * 100) if total_topics > 0 else 0
        )
        keyword_progress_percentage = (
            (completed_keywords / total_topic_keywords * 100) if total_topic_keywords > 0 else 0
        )
        
        return Response({
            'success': True,
            'data': {
                'domain': {
                    'id': domain.id,
                    'name': domain.name,
                    'processing_status': domain.processing_status
                },
                'topics': {
                    'total': total_topics,
                    'status_counts': status_counts,
                    'progress_percentage': round(progress_percentage, 2)
                },
                'topic_keywords': {
                    'total': total_topic_keywords,
                    'status_counts': keyword_status_counts,
                    'progress_percentage': round(keyword_progress_percentage, 2)
                },
                'keyword_analytics': {
                    'total': total_keyword_analytics,
                    'platform_status': platform_status
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in topic_analytics_status: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def topic_analytics_summary(request, domain_id):
    """
    Get aggregated topic analytics summary for a domain
    """
    try:
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Get all topics for the domain
        topics = Topic.objects.filter(domain=domain)
        
        # Calculate aggregated metrics across all topics
        aggregated_metrics = topics.aggregate(
            total_topics=Count('id'),
            total_mentions=Sum('total_mentions'),
            avg_visibility_score=Avg('visibility_score'),
            avg_sentiment_score=Avg('sentiment_score'),
            avg_trend_percentage=Avg('trend_percentage')
        )
        
        # Get metrics by platform (from keyword analytics)
        platform_metrics = {}
        keyword_analytics = KeywordAnalytics.objects.filter(keyword__domain=domain, track_status='COMP')
        
        for platform in ['ChatGPT', 'Google Gemini', 'Perplexity', 'Claude', 'Grok', 'DeepSeek']:
            platform_analytics = keyword_analytics.filter(platform=platform)
            platform_metrics[platform] = platform_analytics.aggregate(
                total_mentions=Sum('mentions'),
                avg_position=Avg('avg_position'),
                avg_visibility_score=Avg('visibility_score'),
                avg_sentiment_score=Avg('sentiment_score')
            )
        
        # Get topic summaries
        topic_summaries = []
        for topic in topics:
            # Get keyword analytics for this topic
            topic_keywords = TopicKeyword.objects.filter(topic=topic)
            keyword_ids = [tk.keyword_id for tk in topic_keywords]
            topic_keyword_analytics = keyword_analytics.filter(keyword_id__in=keyword_ids)
            
            topic_summary = {
                'topic_id': topic.id,
                'topic_name': topic.name,
                'keyword_count': topic_keywords.count(),
                'keywords_completed': topic_keywords.filter(track_status='COMP').count(),
                'total_mentions': topic.total_mentions,
                'visibility_score': float(topic.visibility_score) if topic.visibility_score else 0.0,
                'sentiment_score': float(topic.sentiment_score) if topic.sentiment_score else 0.0,
                'trend_percentage': float(topic.trend_percentage) if topic.trend_percentage else 0.0,
                'platform_list': topic.platform_list or [],
                'track_status': topic.track_status,
                'keyword_analytics': {
                    'total': topic_keyword_analytics.count(),
                    'total_mentions': topic_keyword_analytics.aggregate(Sum('mentions'))['mentions__sum'] or 0,
                    'avg_visibility': float(topic_keyword_analytics.aggregate(Avg('visibility_score'))['visibility_score__avg'] or 0.0),
                    'avg_sentiment': float(topic_keyword_analytics.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0.0)
                }
            }
            topic_summaries.append(topic_summary)
        
        # Sort by total mentions
        topic_summaries.sort(key=lambda x: x['total_mentions'], reverse=True)
        
        return Response({
            'success': True,
            'data': {
                'domain': {
                    'id': domain.id,
                    'name': domain.name
                },
                'aggregated_metrics': aggregated_metrics,
                'platform_metrics': platform_metrics,
                'topic_summaries': topic_summaries
            }
        })
        
    except Exception as e:
        logger.error(f"Error in topic_analytics_summary: {str(e)}", exc_info=True)
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


@api_view(['POST'])
@permission_classes([AllowAny])
def start_topic_generation(request):
    """
    Queue topic generation for a domain.

    Topic generation otherwise only fires once, on the PROC -> COMP transition
    at the end of a domain's first prompt run. A domain already past that point
    — or one whose grouping failed at the time — has no way to produce topics,
    and the page sits on a "Processing topic data..." card describing work that
    is not queued.

    The run is additive: TopicProcessor contains no deletes, matching topics have
    their keyword list merged rather than replaced, and only keywords with
    last_used_for_topic_generation NULL are considered. Triggering it on a domain
    that already has topics cannot damage them.

    Body:
        domain_id: Required
    """
    try:
        domain_id = request.data.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        domain = get_object_or_404(Domain, id=domain_id)

        from shared_models.models import Keyword
        pending = Keyword.objects.filter(
            domain_id=domain_id,
            last_used_for_topic_generation__isnull=True
        ).count()

        if pending == 0:
            return Response(
                {
                    'error': 'Every keyword for this domain has already been grouped. '
                             'Add keywords to generate more topics.',
                    'status': 'no_pending_keywords',
                },
                status=status.HTTP_409_CONFLICT
            )

        from core import topic_progress

        # Recorded BEFORE the task is queued so a page refresh in the first
        # seconds — before a worker has picked the message up — still finds a
        # run in progress rather than an empty "No topics yet" card.
        task = process_topics_for_domain_task.delay(domain_id)
        topic_progress.start(domain_id, pending, task_id=task.id)

        return Response({
            'success': True,
            'message': f'Grouping {pending} keyword(s) into topics for {domain.name}.',
            'domain_id': domain_id,
            'pending_keywords': pending,
            'task_id': task.id,
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Error starting topic generation: {str(e)}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def topic_generation_status(request):
    """Progress of the topic-grouping run for a domain.

    Grouping writes nothing to the database until every batch has returned, so
    the database cannot answer "is a run in progress?" — for thirteen minutes a
    running domain and an untouched one look identical. This reads the Redis
    record the task keeps, which is why a page refresh mid-run can restore the
    progress bar instead of offering to start the run again.

    Query params:
        domain_id: Required
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    from core import topic_progress

    progress = topic_progress.read(domain_id) or {}
    done = int(progress.get('batches_done') or 0)
    total = int(progress.get('batches_total') or 0)

    return Response({
        'domain_id': int(domain_id),
        # 'idle' when nothing has ever run, or the record has expired.
        'state': progress.get('state') or 'idle',
        'stage': progress.get('stage') or '',
        'batches_done': done,
        'batches_total': total,
        'percent': int(done * 100 / total) if total else 0,
        'keywords': int(progress.get('keywords') or 0),
        'topics_created': int(progress.get('topics_created') or 0),
        'started_at': progress.get('started_at'),
        'updated_at': progress.get('updated_at'),
        'error': progress.get('error'),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def start_misinformation_scan(request):
    """
    Start misinformation scan for a domain.
    
    Body:
        domain_id: Required - ID of the domain to scan
        prompt_analytics_ids: Optional - List of specific prompt analytics IDs to scan
        own_links_only: Optional - Only visit citations pointing at the domain's
            own site. This is what the Citations page's "Validate Citations"
            button sends: it asks whether links AI sent to *this* brand still
            work, so crawling the other few hundred third-party sources in the
            same responses is pure cost. Automatic scans leave it off, because
            misinformation detection has to read third-party pages.
    """
    try:
        domain_id = request.data.get('domain_id')
        prompt_analytics_ids = request.data.get('prompt_analytics_ids')
        own_links_only = bool(request.data.get('own_links_only'))

        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure domain exists
        domain = get_object_or_404(Domain, id=domain_id)
        
        # Check for running scan
        from shared_models.models import MisinformationScan
        running_scan = MisinformationScan.objects.filter(
            domain=domain,
            status='running'
        ).first()
        
        if running_scan:
            return Response(
                {
                    'error': 'A scan is already running for this domain',
                    'scan_id': running_scan.id
                },
                status=status.HTTP_409_CONFLICT
            )
        
        # Trigger the Celery task
        task = process_misinformation_scan_task.delay(
            domain_id, prompt_analytics_ids, own_links_only
        )
        
        return Response({
            'success': True,
            'message': f'Misinformation scan started for domain {domain.name}',
            'domain_id': domain_id,
            'task_id': task.id,
            'mode': 'async'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting misinformation scan: {str(e)}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
    List competitor-prompt analytics, including domain's own mentions
    """
    competitor_id = request.query_params.get('competitor_id')
    domain_id = request.query_params.get('domain_id')
    is_mentioned = request.query_params.get('is_mentioned')
    page_size = request.query_params.get('page_size', '500')  # Default to 500 for optimal performance

    # Support pagination with page_size
    try:
        limit = min(int(page_size), 2000)  # Max 2000 records for optimal performance
    except (ValueError, TypeError):
        limit = 500  # Default limit

    results = []

    # Part 1: Get competitor mentions
    queryset = CompetitorPromptAnalytics.objects.all()

    if competitor_id:
        queryset = queryset.filter(competitor_id=competitor_id)

    if domain_id:
        queryset = queryset.filter(competitor__domain_id=domain_id)

    # Filter by is_mentioned if provided
    if is_mentioned is not None:
        if is_mentioned.lower() == 'true':
            queryset = queryset.filter(is_mentioned=True)
        elif is_mentioned.lower() == 'false':
            queryset = queryset.filter(is_mentioned=False)

    queryset = queryset.select_related('competitor', 'prompt').order_by('-tracked_at')
    # Don't limit here - we'll limit after merging with PromptAnalytics and sorting
    competitor_data = CompetitorPromptAnalyticsSerializer(queryset, many=True).data
    results.extend(competitor_data)

    # Part 2: Get domain's own mentions (from PromptAnalytics)
    if domain_id and not competitor_id:
        from shared_models.models import PromptAnalytics, Domain

        # Get PromptAnalytics for this domain
        prompt_analytics_qs = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id
        ).select_related('prompt', 'prompt__group', 'prompt__group__domain').order_by('-tracked_at')

        # Apply is_mentioned filter if provided
        if is_mentioned is not None:
            if is_mentioned.lower() == 'true':
                prompt_analytics_qs = prompt_analytics_qs.filter(is_mention=True)
            elif is_mentioned.lower() == 'false':
                prompt_analytics_qs = prompt_analytics_qs.filter(is_mention=False)

        # Transform PromptAnalytics to match CompetitorPromptAnalytics format
        # Don't limit here - we'll limit after merging and sorting
        for pa in prompt_analytics_qs:
            try:
                # Map PromptAnalytics fields to CompetitorPromptAnalytics format
                results.append({
                'id': pa.id,
                'competitor': None,  # No competitor - this is the domain's own mention
                'competitor_name': None,  # Will be handled by frontend as "You"
                'prompt': pa.prompt.id,
                'prompt_text': pa.prompt.prompt,
                'domain_name': pa.prompt.group.domain.name,
                'track_status': pa.track_status,
                'track_message': pa.track_message,
                'tracked_at': pa.tracked_at.isoformat() if pa.tracked_at else None,
                'is_mentioned': pa.is_mention,
                'position': float(pa.position) if pa.position else None,
                'mention_count': pa.total_mentions,
                'sentiment_category': pa.sentiment_category,
                'sentiment_score': float(pa.sentiment_score) if pa.sentiment_score else 0.0,
                'platform': pa.platform,
                'response_text': '',  # PromptAnalytics doesn't store full response
                'citation_list': pa.citation_list if pa.citation_list else [],
                'created_at': pa.created_at.isoformat() if pa.created_at else None,
                'modified_at': pa.modified_at.isoformat() if pa.modified_at else None,
                })
            except Exception as e:
                # Log error but continue processing other rows
                pass

    # Sort all results by tracked_at
    results.sort(key=lambda x: x.get('tracked_at') or '', reverse=True)

    # Use JsonResponse instead of DRF Response to bypass automatic pagination
    return JsonResponse(results[:limit], safe=False)


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
    
    # Share is stored once per platform plus an aggregate row per brand. Without
    # a platform filter this returned every brand several times over — once per
    # platform — and callers summing the result counted each brand repeatedly.
    # Defaults to the aggregate; pass ?platform=ChatGPT for one platform's split.
    from core.competitor_processor import SOV_OVERALL_PLATFORM
    platform = request.query_params.get('platform') or SOV_OVERALL_PLATFORM

    scoped = ShareOfVoiceAnalytics.objects.filter(domain_id=domain_id, platform=platform)

    # Rows written before share was computed per platform carry the literal
    # 'ChatGPT' for what was actually an all-platform total; fall back to them so
    # a domain that has not been recalculated still renders.
    if not scoped.exists() and platform == SOV_OVERALL_PLATFORM:
        scoped = ShareOfVoiceAnalytics.objects.filter(domain_id=domain_id)

    latest = scoped.order_by('-timestamp').first()

    if not latest:
        return Response({
            'domain_id': int(domain_id),
            'message': 'No share of voice data available yet',
            'players': []
        })

    sov_data = scoped.filter(
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
# Integration Insights Endpoints

@api_view(['POST'])
@permission_classes([AllowAny])
def start_integration_insights_scheduler(request):
    """
    Manually trigger the integration insights scheduler to process INIT records.
    POST /api/integrations/scheduler/start/
    Body: {}  # No parameters needed - processes pending INIT records
    
    This will trigger the scheduler which picks up one GA and one GSC INIT record
    and processes them. You can call this multiple times to process more records.
    """
    try:
        from .processing_tasks import process_integration_insights_scheduler
        task = process_integration_insights_scheduler.delay()
        return Response({
            'success': True,
            'task_id': task.id,
            'message': 'Scheduler triggered. It will process one GA and one GSC INIT record if available.'
        })
    except Exception as e:
        logger.error(f"Error triggering scheduler: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to trigger scheduler: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def process_pending_insights(request):
    """
    Manually process specific pending INIT records.
    POST /api/integrations/process-pending/
    Body: {
        "insight_id": 1,  # Optional - specific insight ID to process
        "insight_type": "ga" or "gsc",  # Optional - filter by type
        "process_all": false  # Optional - process all pending INIT records (use with caution)
    }
    """
    try:
        from integrations.models import GATrafficInsight, GSCTrafficInsight
        from .processing_tasks import process_ga_insight_task, process_gsc_insight_task
        
        insight_id = request.data.get('insight_id')
        insight_type = request.data.get('insight_type')  # 'ga' or 'gsc'
        process_all = request.data.get('process_all', False)
        
        if insight_id:
            # Process specific insight
            insight = None
            if insight_type == 'ga' or not insight_type:
                try:
                    insight = GATrafficInsight.objects.get(id=insight_id, track_status='INIT')
                    task = process_ga_insight_task.delay(insight_id)
                    return Response({
                        'success': True,
                        'task_id': task.id,
                        'insight_id': insight_id,
                        'type': 'ga'
                    })
                except GATrafficInsight.DoesNotExist:
                    pass
            
            if insight_type == 'gsc' or not insight_type:
                try:
                    insight = GSCTrafficInsight.objects.get(id=insight_id, track_status='INIT')
                    task = process_gsc_insight_task.delay(insight_id)
                    return Response({
                        'success': True,
                        'task_id': task.id,
                        'insight_id': insight_id,
                        'type': 'gsc'
                    })
                except GSCTrafficInsight.DoesNotExist:
                    pass
            
            return Response(
                {'error': f'Insight {insight_id} not found or not in INIT status'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        elif process_all:
            # Process all pending INIT records
            task_ids = []
            
            if insight_type != 'gsc':
                ga_insights = GATrafficInsight.objects.filter(
                    track_status='INIT',
                    integration__status='active',
                    integration__provider_id__isnull=False
                ).exclude(integration__provider_id='')
                
                for insight in ga_insights:
                    # Check if not already processing
                    if not GATrafficInsight.objects.filter(
                        integration=insight.integration,
                        track_status='PROC'
                    ).exists():
                        task = process_ga_insight_task.delay(insight.id)
                        task_ids.append({'insight_id': insight.id, 'type': 'ga', 'task_id': task.id})
            
            if insight_type != 'ga':
                gsc_insights = GSCTrafficInsight.objects.filter(
                    track_status='INIT',
                    integration__status='active',
                    integration__provider_id__isnull=False
                ).exclude(integration__provider_id='')
                
                for insight in gsc_insights:
                    # Check if not already processing
                    if not GSCTrafficInsight.objects.filter(
                        integration=insight.integration,
                        track_status='PROC'
                    ).exists():
                        task = process_gsc_insight_task.delay(insight.id)
                        task_ids.append({'insight_id': insight.id, 'type': 'gsc', 'task_id': task.id})
            
            return Response({
                'success': True,
                'tasks_started': len(task_ids),
                'tasks': task_ids
            })
        
        else:
            return Response(
                {'error': 'Either insight_id or process_all=true is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        logger.error(f"Error processing insights: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to process insights: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_pending_insights(request):
    """
    Get list of pending INIT records.
    GET /api/integrations/pending-insights/?type=ga|gsc
    """
    try:
        from integrations.models import GATrafficInsight, GSCTrafficInsight
        
        insight_type = request.query_params.get('type')  # 'ga' or 'gsc'
        
        pending = {
            'ga': [],
            'gsc': []
        }
        
        if insight_type != 'gsc':
            ga_insights = GATrafficInsight.objects.filter(
                track_status='INIT',
                integration__status='active',
                integration__provider_id__isnull=False
            ).exclude(integration__provider_id='').select_related('integration', 'domain').order_by('created_at')
            
            for insight in ga_insights:
                pending['ga'].append({
                    'id': insight.id,
                    'integration_id': insight.integration.id,
                    'domain_id': insight.domain.id,
                    'domain_name': insight.domain.name,
                    'start_date': insight.start_date.isoformat(),
                    'end_date': insight.end_date.isoformat(),
                    'created_at': insight.created_at.isoformat(),
                })
        
        if insight_type != 'ga':
            gsc_insights = GSCTrafficInsight.objects.filter(
                track_status='INIT',
                integration__status='active',
                integration__provider_id__isnull=False
            ).exclude(integration__provider_id='').select_related('integration', 'domain').order_by('created_at')
            
            for insight in gsc_insights:
                pending['gsc'].append({
                    'id': insight.id,
                    'integration_id': insight.integration.id,
                    'domain_id': insight.domain.id,
                    'domain_name': insight.domain.name,
                    'start_date': insight.start_date.isoformat(),
                    'end_date': insight.end_date.isoformat(),
                    'created_at': insight.created_at.isoformat(),
                })
        
        return Response({
            'pending_count': {
                'ga': len(pending['ga']),
                'gsc': len(pending['gsc']),
                'total': len(pending['ga']) + len(pending['gsc'])
            },
            'pending': pending
        })
    
    except Exception as e:
        logger.error(f"Error getting pending insights: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to get pending insights: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== SEO RANKING ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def seo_process_keyword(request):
    """
    Trigger SEO rank processing for a single keyword.
    Body: { seo_keyword_rank_id: int }
    """
    from .processing_tasks import process_seo_keyword_task

    seo_kw_id = request.data.get('seo_keyword_rank_id')
    if not seo_kw_id:
        return Response(
            {'error': 'seo_keyword_rank_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        process_seo_keyword_task.delay(int(seo_kw_id))
        return Response({
            'message': f'SEO keyword {seo_kw_id} queued for processing',
            'seo_keyword_rank_id': seo_kw_id,
        })
    except Exception as e:
        logger.error(f"[SEO] Error queuing keyword {seo_kw_id}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def seo_process_new_keywords(request):
    """
    Scrape a specific set of just-added keywords immediately.

    Body: { domain_id: int, seo_keyword_rank_ids: [int, ...] }

    Separate from `seo_process_domain` on purpose: this dispatches to the
    `seo_instant` queue so it never waits behind the nightly sweep, and it
    scrapes only the ids given rather than every 'avail' row on the domain.
    """
    from .processing_tasks import process_new_keywords_task

    domain_id = request.data.get('domain_id')
    keyword_ids = request.data.get('seo_keyword_rank_ids') or []

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not isinstance(keyword_ids, list) or not keyword_ids:
        return Response(
            {'error': 'seo_keyword_rank_ids must be a non-empty list'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        ids = [int(k) for k in keyword_ids]
    except (TypeError, ValueError):
        return Response(
            {'error': 'seo_keyword_rank_ids must all be integers'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        process_new_keywords_task.apply_async(
            args=[int(domain_id), ids],
            queue='seo_instant',
        )
        logger.info(
            f"[SEO instant] Queued {len(ids)} new keywords for domain {domain_id}"
        )
        return Response({
            'message': f'{len(ids)} new keywords queued for immediate scraping',
            'domain_id': domain_id,
            'keyword_count': len(ids),
        })
    except Exception as e:
        logger.error(f"[SEO instant] Error queuing new keywords for domain {domain_id}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def seo_process_domain(request):
    """
    Trigger SEO rank processing for all keywords of a domain.
    Body: { domain_id: int }
    """
    from .processing_tasks import process_seo_domain_task

    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        process_seo_domain_task.delay(int(domain_id))
        return Response({
            'message': f'SEO domain {domain_id} queued for processing',
            'domain_id': domain_id,
        })
    except Exception as e:
        logger.error(f"[SEO] Error queuing domain {domain_id}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def seo_fetch_backlinks(request):
    """Queue a DataForSEO backlink pull for an already-created snapshot.

    Body: { snapshot_id: int }

    The backend creates the snapshot row (so the UI has something to poll the
    moment the button is pressed) and enforces the monthly refresh guard; this
    only dispatches the work to the seo queue.
    """
    from .processing_tasks import fetch_backlinks_task

    snapshot_id = request.data.get('snapshot_id')
    if not snapshot_id:
        return Response(
            {'error': 'snapshot_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        fetch_backlinks_task.delay(int(snapshot_id))
        return Response({
            'message': f'Backlink snapshot {snapshot_id} queued',
            'snapshot_id': int(snapshot_id),
        })
    except Exception as e:
        logger.error(f"[BL] Error queuing snapshot {snapshot_id}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def seo_sync_volume(request):
    """Fetch search volume for one domain's keywords now.

    Body: { domain_id: int }

    Used when keywords are first imported, so a new brand does not sit with
    blank volumes until the next hourly sweep. Batched internally.
    """
    from .processing_tasks import sync_domain_volume_task

    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        sync_domain_volume_task.delay(int(domain_id))
        return Response({
            'message': f'Volume sync queued for domain {domain_id}',
            'domain_id': domain_id,
        })
    except Exception as e:
        logger.error(f"[VOLUME] Error queuing domain {domain_id}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== SEO COMPETITOR ANALYSIS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def seo_analyze_competitors(request):
    """
    Trigger competitor analysis for a domain.
    Body: { domain_id: int }
    """
    from .processing_tasks import analyze_seo_competitors_task

    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        analyze_seo_competitors_task.delay(int(domain_id))
        return Response({
            'message': f'Competitor analysis for domain {domain_id} queued',
            'domain_id': domain_id,
        })
    except Exception as e:
        logger.error(f"[CompAnalysis] Error queuing domain {domain_id}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
