from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from decouple import config
import logging
import requests
import re
import threading

from .models import (
    GeneratedContent, CMSProvider, ScheduledPublication, ContentComment,
    BulkUploadBatch, BulkUploadItem
)
from .serializers import (
    GeneratedContentSerializer, ContentGenerationRequestSerializer,
    CMSProviderSerializer, CMSProviderCreateSerializer,
    ScheduledPublicationSerializer, PublishContentSerializer,
    ContentCommentSerializer, CreateContentCommentSerializer,
    BulkUploadBatchSerializer, BulkUploadBatchListSerializer, BulkUploadItemSerializer
)
from .claude_content_generator import ClaudeContentGenerator
from domains.models import Domain, ReferenceDocument
from django.db import transaction, connection
from django.db.models import Count, Q
from django.utils import timezone as django_timezone
from datetime import datetime

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_content(request):
    """
    Generate content using Claude API

    Expected request body:
    {
        "domain_id": int,
        "title": str,
        "keywords": str,
        "article_type": str,
        "tone": str,
        "style": str,
        "goal": str,
        "audience": str,
        "depth": str,
        "word_count": int,
        "source_type": str,
        "source_id": int (optional),
        "source_reference": str (optional),
        "priority": str (optional),
        "scheduled_date": str (optional)
    }
    """
    try:
        # Validate request data
        serializer = ContentGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Get domain and verify it belongs to user's organization
        domain_id = validated_data['domain_id']
        try:
            domain = Domain.objects.get(
                id=domain_id,
                organisation=request.user.organisation
            )
        except Domain.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Domain not found or you do not have access to this domain'
            }, status=status.HTTP_404_NOT_FOUND)

        # Import and initialize Claude content generator
        generator = ClaudeContentGenerator()

        # Check reference repository for relevant content
        reference_repository_context = ''
        reference_docs = ReferenceDocument.objects.filter(domain=domain)
        logger.info(f"[REF-REPO] Domain {domain.id}: Found {reference_docs.count()} reference document(s)")
        if reference_docs.exists():
            for doc in reference_docs:
                logger.info(f"[REF-REPO] Doc: {doc.file_name} | Type: {doc.file_type} | Text length: {len(doc.extracted_text or '')} chars")
            try:
                reference_repository_context = generator.match_reference_content(
                    title=validated_data['title'],
                    keywords=validated_data['keywords'],
                    article_type=validated_data.get('article_type', 'blog'),
                    reference_docs=reference_docs
                )
                if reference_repository_context:
                    logger.info(f"[REF-REPO] MATCH FOUND - Relevant content ({len(reference_repository_context)} chars) will be injected into generation prompt")
                else:
                    logger.info(f"[REF-REPO] NO MATCH - No relevant content found for title: {validated_data['title']}")
            except Exception as e:
                logger.warning(f"[REF-REPO] Reference matching failed (non-fatal): {str(e)}")

        # Prepare generation parameters
        generation_params = {
            'title': validated_data['title'],
            'keywords': validated_data['keywords'],
            'article_type': validated_data.get('article_type', 'blog'),
            'target_country': validated_data.get('target_country', 'united_states'),
            'target_language': validated_data.get('target_language', 'us_english'),
            'references': validated_data.get('references', []),
            'tone': validated_data.get('tone', 'professional'),
            'style': validated_data.get('style', 'informative'),
            'goal': validated_data.get('goal', 'educate'),
            'audience': validated_data.get('audience', 'general'),
            'depth': validated_data.get('depth', 'comprehensive'),
            'word_count': validated_data.get('word_count', 1500),
            'source_reference': validated_data.get('source_reference', ''),
            # Domain content guidelines
            'key_messages': validated_data.get('key_messages', ''),
            'topics_to_avoid': validated_data.get('topics_to_avoid', ''),
            'additional_instructions': validated_data.get('additional_instructions', ''),
            'brand_values': validated_data.get('brand_values', ''),
            'reference_repository_context': reference_repository_context,
        }

        # Enrich reference URLs with actual fetched content to prevent hallucination
        if generation_params.get('references'):
            generation_params['references'] = _enrich_references_with_content(generation_params['references'])

        # Generate content using Claude
        logger.info(f"Generating content for domain {domain.id}: {validated_data['title']}")
        generation_result = generator.generate_content(generation_params)

        # Generate SEO meta tags (separate lightweight call)
        meta_result = generator.generate_meta_tags(
            title=validated_data['title'],
            content_html=generation_result['content_html'],
            keywords=validated_data['keywords'],
        )

        # Create GeneratedContent record
        generated_content = GeneratedContent.objects.create(
            domain=domain,
            title=validated_data['title'],
            content_html=generation_result['content_html'],
            meta_title=meta_result['meta_title'],
            meta_description=meta_result['meta_description'],
            source_type=validated_data.get('source_type', 'manual'),
            source_id=validated_data.get('source_id'),
            source_reference=validated_data.get('source_reference', ''),
            article_type=validated_data.get('article_type', 'blog'),
            keywords=validated_data['keywords'],
            tone=validated_data.get('tone', 'professional'),
            style=validated_data.get('style', 'informative'),
            goal=validated_data.get('goal', 'educate'),
            audience=validated_data.get('audience', 'general'),
            depth=validated_data.get('depth', 'comprehensive'),
            word_count=validated_data.get('word_count', 1500),
            actual_word_count=generation_result['actual_word_count'],
            status='generated',
            priority=validated_data.get('priority', 'medium'),
            scheduled_date=validated_data.get('scheduled_date'),
            model_used=generation_result['model_used'],
            generation_time_seconds=generation_result['generation_time_seconds'],
            prompt_tokens=generation_result['prompt_tokens'],
            completion_tokens=generation_result['completion_tokens']
        )

        # Return response with generated content
        response_serializer = GeneratedContentSerializer(generated_content)
        logger.info(f"Successfully generated content ID {generated_content.id}")

        return Response({
            'status': 'success',
            'message': 'Content generated successfully',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error generating content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error generating content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_outline(request):
    """
    Generate a content outline using Claude API

    Expected request body: Same as generate_content
    Returns: JSON outline with sections
    """
    try:
        # Validate request data
        logger.info(f"Outline generation request data: {request.data}")
        serializer = ContentGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Outline generation validation errors: {serializer.errors}")
            error_details = "; ".join([f"{k}: {v}" for k, v in serializer.errors.items()])
            return Response({
                'status': 'error',
                'message': f'Invalid request data: {error_details}',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Get domain and verify it belongs to user's organization
        domain_id = validated_data['domain_id']
        try:
            domain = Domain.objects.get(
                id=domain_id,
                organisation=request.user.organisation
            )
        except Domain.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Domain not found or you do not have access to this domain'
            }, status=status.HTTP_404_NOT_FOUND)

        # Initialize Claude content generator
        generator = ClaudeContentGenerator()

        # Check reference repository for relevant content
        reference_repository_context = ''
        reference_docs = ReferenceDocument.objects.filter(domain=domain)
        if reference_docs.exists():
            try:
                reference_repository_context = generator.match_reference_content(
                    title=validated_data['title'],
                    keywords=validated_data['keywords'],
                    article_type=validated_data.get('article_type', 'blog'),
                    reference_docs=reference_docs
                )
                if reference_repository_context:
                    logger.info(f"Found relevant reference content for outline generation, domain {domain.id}")
            except Exception as e:
                logger.warning(f"Reference matching failed (non-fatal): {str(e)}")

        # Prepare generation parameters
        generation_params = {
            'title': validated_data['title'],
            'keywords': validated_data['keywords'],
            'article_type': validated_data.get('article_type', 'blog'),
            'target_country': validated_data.get('target_country', 'united_states'),
            'target_language': validated_data.get('target_language', 'us_english'),
            'references': validated_data.get('references', []),
            'tone': validated_data.get('tone', 'professional'),
            'style': validated_data.get('style', 'informative'),
            'audience': validated_data.get('audience', 'general'),
            'word_count': validated_data.get('word_count', 1500),
            'key_messages': validated_data.get('key_messages', ''),
            'topics_to_avoid': validated_data.get('topics_to_avoid', ''),
            'additional_instructions': validated_data.get('additional_instructions', ''),
            'reference_repository_context': reference_repository_context,
        }

        # Enrich reference URLs with actual fetched content so the outline
        # is shaped by what the URLs actually contain (same treatment the
        # content-generation step already applies).
        if generation_params.get('references'):
            generation_params['references'] = _enrich_references_with_content(generation_params['references'])

        # Generate outline
        logger.info(f"Generating outline for domain {domain.id}: {validated_data['title']}")
        outline_result = generator.generate_outline(generation_params)

        logger.info(f"Successfully generated outline with {len(outline_result['outline'])} sections")

        return Response({
            'status': 'success',
            'message': 'Outline generated successfully',
            'data': outline_result
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error generating outline: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error generating outline: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_content_from_outline(request):
    """
    Generate full content from an approved outline

    Expected request body:
    - All fields from generate_content
    - outline: List of outline sections
    """
    try:
        # Validate request data
        serializer = ContentGenerationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Get outline from request
        outline = request.data.get('outline')
        if not outline or not isinstance(outline, list):
            return Response({
                'status': 'error',
                'message': 'Outline is required and must be a list of sections'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get domain and verify it belongs to user's organization
        domain_id = validated_data['domain_id']
        try:
            domain = Domain.objects.get(
                id=domain_id,
                organisation=request.user.organisation
            )
        except Domain.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Domain not found or you do not have access to this domain'
            }, status=status.HTTP_404_NOT_FOUND)

        # Initialize Claude content generator
        generator = ClaudeContentGenerator()

        # Check reference repository for relevant content
        reference_repository_context = ''
        reference_docs = ReferenceDocument.objects.filter(domain=domain)
        if reference_docs.exists():
            try:
                reference_repository_context = generator.match_reference_content(
                    title=validated_data['title'],
                    keywords=validated_data['keywords'],
                    article_type=validated_data.get('article_type', 'blog'),
                    reference_docs=reference_docs
                )
                if reference_repository_context:
                    logger.info(f"Found relevant reference content for outline-to-content, domain {domain.id}")
            except Exception as e:
                logger.warning(f"Reference matching failed (non-fatal): {str(e)}")

        # Prepare generation parameters
        generation_params = {
            'title': validated_data['title'],
            'keywords': validated_data['keywords'],
            'article_type': validated_data.get('article_type', 'blog'),
            'target_country': validated_data.get('target_country', 'united_states'),
            'target_language': validated_data.get('target_language', 'us_english'),
            'tone': validated_data.get('tone', 'professional'),
            'style': validated_data.get('style', 'informative'),
            'audience': validated_data.get('audience', 'general'),
            'word_count': validated_data.get('word_count', 1500),
            'key_messages': validated_data.get('key_messages', ''),
            'topics_to_avoid': validated_data.get('topics_to_avoid', ''),
            'additional_instructions': validated_data.get('additional_instructions', ''),
            'brand_values': validated_data.get('brand_values', ''),
            'references': validated_data.get('references', []),
            'reference_repository_context': reference_repository_context,
        }

        # Enrich reference URLs with actual fetched content to prevent hallucination
        if generation_params.get('references'):
            generation_params['references'] = _enrich_references_with_content(generation_params['references'])

        # Generate content from outline
        logger.info(f"Generating content from outline for domain {domain.id}: {validated_data['title']}")
        generation_result = generator.generate_content_from_outline(generation_params, outline)

        # Generate SEO meta tags (separate lightweight call)
        meta_result = generator.generate_meta_tags(
            title=validated_data['title'],
            content_html=generation_result['content_html'],
            keywords=validated_data['keywords'],
        )

        # Create GeneratedContent record
        generated_content = GeneratedContent.objects.create(
            domain=domain,
            title=validated_data['title'],
            content_html=generation_result['content_html'],
            meta_title=meta_result['meta_title'],
            meta_description=meta_result['meta_description'],
            source_type=validated_data.get('source_type', 'manual'),
            source_id=validated_data.get('source_id'),
            source_reference=validated_data.get('source_reference', ''),
            article_type=validated_data.get('article_type', 'blog'),
            keywords=validated_data['keywords'],
            tone=validated_data.get('tone', 'professional'),
            style=validated_data.get('style', 'informative'),
            goal=validated_data.get('goal', 'educate'),
            audience=validated_data.get('audience', 'general'),
            depth=validated_data.get('depth', 'comprehensive'),
            word_count=validated_data.get('word_count', 1500),
            actual_word_count=generation_result['actual_word_count'],
            status='generated',
            priority=validated_data.get('priority', 'medium'),
            scheduled_date=validated_data.get('scheduled_date'),
            model_used=generation_result['model_used'],
            generation_time_seconds=generation_result['generation_time_seconds'],
            prompt_tokens=generation_result['prompt_tokens'],
            completion_tokens=generation_result['completion_tokens']
        )

        # Return response with generated content
        response_serializer = GeneratedContentSerializer(generated_content)
        logger.info(f"Successfully generated content ID {generated_content.id} from outline")

        return Response({
            'status': 'success',
            'message': 'Content generated successfully from outline',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error generating content from outline: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error generating content from outline: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rewrite_content(request):
    """
    Rewrite a portion of content using Claude API

    Expected request body:
    {
        "original_text": str,
        "prompt": str,
        "domain_id": int (optional)
    }
    """
    try:
        original_text = request.data.get('original_text')
        prompt = request.data.get('prompt')
        domain_id = request.data.get('domain_id')

        if not original_text:
            return Response({
                'status': 'error',
                'message': 'Original text is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not prompt:
            return Response({
                'status': 'error',
                'message': 'Rewrite prompt is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Initialize Claude content generator
        generator = ClaudeContentGenerator()

        # Generate rewritten content
        logger.info(f"Rewriting content with prompt: {prompt[:50]}...")
        rewritten_text = generator.rewrite_text(original_text, prompt)

        logger.info(f"Successfully rewrote content")

        return Response({
            'status': 'success',
            'message': 'Content rewritten successfully',
            'rewritten_text': rewritten_text
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error rewriting content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error rewriting content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============= Humanise Feature =============

def _run_humanise_in_background(content_id):
    """
    Background thread function that runs a three-pass humanisation process:
    Pass 1: Full humanisation with all 19 rules (Claude API)
    Pass 2: Focused refinement fixing persistent issues (Claude API)
    Pass 3: Programmatic descriptor deduplication (Python, deterministic)

    Django DB connections are per-thread. We must close the connection
    when the thread finishes to prevent connection leaks.
    """
    try:
        content_obj = GeneratedContent.objects.get(id=content_id)
        generator = ClaudeContentGenerator()

        # Pass 1: Full humanisation (all 19 rules)
        logger.info(f"Humanisation Pass 1 started for content {content_id}")
        humanised_html = generator.humanise_content(content_obj.pre_humanise_content)
        logger.info(f"Humanisation Pass 1 completed for content {content_id}")

        # Pass 2: Focused refinement (fixes structural issues)
        logger.info(f"Humanisation Pass 2 (refinement) started for content {content_id}")
        refined_html = generator.refine_humanised_content(humanised_html)
        logger.info(f"Humanisation Pass 2 (refinement) completed for content {content_id}")

        # Pass 3: Programmatic post-processing (deterministic fixes)
        logger.info(f"Humanisation Pass 3 (post-processing) started for content {content_id}")
        final_html = generator.post_process_content(refined_html)
        logger.info(f"Humanisation Pass 3 (post-processing) completed for content {content_id}")

        content_obj.content_html = final_html
        content_obj.humanise_status = 'completed'
        content_obj.humanise_completed_at = timezone.now()
        content_obj.humanise_error = None
        content_obj.save(update_fields=[
            'content_html', 'humanise_status',
            'humanise_completed_at', 'humanise_error', 'modified_at'
        ])

        logger.info(f"Humanisation (all 3 passes) completed for content {content_id}")

    except Exception as e:
        logger.error(f"Humanisation failed for content {content_id}: {str(e)}", exc_info=True)
        try:
            content_obj = GeneratedContent.objects.get(id=content_id)
            content_obj.humanise_status = 'failed'
            content_obj.humanise_error = str(e)[:2000]
            content_obj.humanise_completed_at = timezone.now()
            content_obj.save(update_fields=[
                'humanise_status', 'humanise_error',
                'humanise_completed_at', 'modified_at'
            ])
        except Exception as save_err:
            logger.error(f"Failed to save humanisation error state: {str(save_err)}")
    finally:
        connection.close()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def humanise_content(request, content_id):
    """
    Start the humanisation process for a specific content.

    Saves pre_humanise_content for undo, sets status to 'processing',
    and kicks off a background thread to run the Claude API call.
    Returns immediately with status='processing'.
    """
    try:
        content = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )

        if content.humanise_status == 'processing':
            return Response({
                'status': 'error',
                'message': 'Humanisation is already in progress'
            }, status=status.HTTP_409_CONFLICT)

        if not content.content_html or len(content.content_html.strip()) < 50:
            return Response({
                'status': 'error',
                'message': 'Content is too short to humanise'
            }, status=status.HTTP_400_BAD_REQUEST)

        content.pre_humanise_content = content.content_html
        content.humanise_status = 'processing'
        content.humanise_started_at = timezone.now()
        content.humanise_completed_at = None
        content.humanise_error = None
        content.save(update_fields=[
            'pre_humanise_content', 'humanise_status',
            'humanise_started_at', 'humanise_completed_at',
            'humanise_error', 'modified_at'
        ])

        thread = threading.Thread(
            target=_run_humanise_in_background,
            args=(content.id,),
            daemon=True
        )
        thread.start()

        logger.info(f"Humanisation started for content {content_id}")

        return Response({
            'status': 'success',
            'message': 'Humanisation started',
            'data': {
                'humanise_status': 'processing',
                'humanise_started_at': content.humanise_started_at.isoformat()
            }
        }, status=status.HTTP_202_ACCEPTED)

    except Http404:
        return Response({
            'status': 'error',
            'message': 'Content not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error starting humanisation: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error starting humanisation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def humanise_status(request, content_id):
    """
    Check the status of the humanisation process.

    Returns the current status. When status is 'completed', also returns
    the humanised content_html so the frontend can update the editor.
    Auto-detects stale processing (>10 min timeout) and marks as failed.
    """
    try:
        content = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )

        # Timeout detection for stale processing
        if content.humanise_status == 'processing' and content.humanise_started_at:
            elapsed = (timezone.now() - content.humanise_started_at).total_seconds()
            if elapsed > 600:  # 10 minutes timeout (2-pass humanisation)
                content.humanise_status = 'failed'
                content.humanise_error = 'Humanisation timed out. Please try again.'
                content.humanise_completed_at = timezone.now()
                content.save(update_fields=[
                    'humanise_status', 'humanise_error',
                    'humanise_completed_at', 'modified_at'
                ])

        response_data = {
            'status': 'success',
            'data': {
                'humanise_status': content.humanise_status,
                'humanise_started_at': content.humanise_started_at.isoformat() if content.humanise_started_at else None,
                'humanise_completed_at': content.humanise_completed_at.isoformat() if content.humanise_completed_at else None,
                'humanise_error': content.humanise_error,
            }
        }

        if content.humanise_status == 'completed':
            response_data['data']['content_html'] = content.content_html

        return Response(response_data, status=status.HTTP_200_OK)

    except Http404:
        return Response({
            'status': 'error',
            'message': 'Content not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error checking humanise status: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error checking humanise status: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def humanise_undo(request, content_id):
    """
    Revert the content to its pre-humanisation state.

    Restores content_html from pre_humanise_content,
    resets humanise_status to 'idle', and clears pre_humanise_content.
    """
    try:
        content = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )

        if not content.pre_humanise_content:
            return Response({
                'status': 'error',
                'message': 'No pre-humanisation content available to restore'
            }, status=status.HTTP_400_BAD_REQUEST)

        if content.humanise_status == 'processing':
            return Response({
                'status': 'error',
                'message': 'Cannot undo while humanisation is in progress'
            }, status=status.HTTP_409_CONFLICT)

        restored_html = content.pre_humanise_content
        content.content_html = restored_html
        content.humanise_status = 'idle'
        content.pre_humanise_content = None
        content.humanise_started_at = None
        content.humanise_completed_at = None
        content.humanise_error = None
        content.save(update_fields=[
            'content_html', 'humanise_status', 'pre_humanise_content',
            'humanise_started_at', 'humanise_completed_at',
            'humanise_error', 'modified_at'
        ])

        logger.info(f"Humanisation undone for content {content_id}")

        return Response({
            'status': 'success',
            'message': 'Content reverted to pre-humanisation state',
            'data': {
                'content_html': restored_html,
                'humanise_status': 'idle'
            }
        }, status=status.HTTP_200_OK)

    except Http404:
        return Response({
            'status': 'error',
            'message': 'Content not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error undoing humanisation: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error undoing humanisation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_generated_contents(request):
    """
    Get generated contents with optional filtering

    Query parameters:
    - domain_id: Filter by domain
    - status: Filter by status (draft, generated, published)
    - source_type: Filter by source type (topic, content_gap, manual)
    - page: Page number for pagination
    - page_size: Number of items per page
    """
    try:
        # Get query parameters
        domain_id = request.GET.get('domain_id')
        status_filter = request.GET.get('status')
        source_type = request.GET.get('source_type')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        # Build query - filter by user's organization
        queryset = GeneratedContent.objects.filter(
            domain__organisation=request.user.organisation
        )

        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if source_type:
            queryset = queryset.filter(source_type=source_type)

        # Annotate with comment counts
        queryset = queryset.annotate(
            total_comments=Count('comments'),
            pending_comments=Count('comments', filter=Q(comments__status='pending')),
        )

        # Order by modified_at descending so recently edited docs appear first
        # (Issue 13: Recent docs not showing in list view)
        ordering = request.GET.get('ordering', '-modified_at')
        allowed_orderings = ['-modified_at', '-created_at', 'title', '-title', 'status']
        if ordering not in allowed_orderings:
            ordering = '-modified_at'
        queryset = queryset.order_by(ordering)

        # Apply pagination
        total_count = queryset.count()
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        paginated_contents = queryset[start_index:end_index]

        # Serialize data
        serializer = GeneratedContentSerializer(paginated_contents, many=True)

        return Response({
            'status': 'success',
            'results': serializer.data,
            'count': total_count,
            'total_pages': total_pages,
            'current_page': page,
            'page_size': page_size,
            'has_next': page < total_pages,
            'has_previous': page > 1
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error fetching generated contents: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error fetching generated contents: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_generated_content(request, content_id):
    """
    Get a specific generated content by ID
    """
    try:
        content = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )
        serializer = GeneratedContentSerializer(content)

        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    except Http404:
        return Response({
            'status': 'error',
            'message': 'Generated content not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching generated content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error fetching generated content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_generated_content(request, content_id):
    """
    Update a generated content
    Allows updating content_html, status, scheduled_date, etc.
    """
    try:
        content = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )

        # Capture state before save for humanise auto-reset
        old_content_html = content.content_html
        old_humanise_status = content.humanise_status

        # Partial update for PATCH, full update for PUT
        partial = request.method == 'PATCH'
        serializer = GeneratedContentSerializer(content, data=request.data, partial=partial)

        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # If content was edited after humanisation, reset humanise state
        # so stale undo data doesn't persist across page reloads
        new_content_html = request.data.get('content_html')
        if (new_content_html is not None
                and old_humanise_status == 'completed'
                and new_content_html != old_content_html):
            content.humanise_status = 'idle'
            content.pre_humanise_content = None
            content.humanise_started_at = None
            content.humanise_completed_at = None
            content.humanise_error = None
            content.save(update_fields=[
                'humanise_status', 'pre_humanise_content',
                'humanise_started_at', 'humanise_completed_at',
                'humanise_error', 'modified_at'
            ])

        return Response({
            'status': 'success',
            'message': 'Content updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    except Http404:
        return Response({
            'status': 'error',
            'message': 'Generated content not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating generated content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error updating generated content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _publish_to_wordpress(content_obj, cms_provider, scheduled_at=None):
    """
    Helper function to publish content to WordPress
    Returns: (success: bool, result: dict, error: str)
    """
    try:
        settings = cms_provider.settings
        wp_api_url = settings.get('api_url')
        wp_username = settings.get('username')
        wp_app_password = settings.get('app_password')
        content_type = settings.get('content_type', 'pages')  # 'pages' or 'posts'
        
        if not wp_api_url or not wp_username or not wp_app_password:
            return False, None, "WordPress settings incomplete"
        
        # Construct API endpoint
        if not wp_api_url.endswith('/'):
            wp_api_url += '/'
        wp_endpoint = f"{wp_api_url}{content_type}"
        
        payload = {
            "title": content_obj.title,
            "content": content_obj.content_html or content_obj.title,
        }
        
        # Set status based on schedule
        if scheduled_at and scheduled_at > django_timezone.now():
            payload["status"] = "future"  # WordPress scheduled status
            payload["date"] = scheduled_at.isoformat()
        else:
            payload["status"] = "publish"
        
        resp = requests.post(
            wp_endpoint,
            json=payload,
            auth=(wp_username, wp_app_password),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        if not resp.ok:
            try:
                err_json = resp.json()
                msg = err_json.get('message') or str(err_json)
            except Exception:
                msg = resp.text
            return False, None, f"WordPress API error: {msg}"
        
        wp_result = resp.json()
        return True, wp_result, None
        
    except Exception as e:
        logger.error(f"Error publishing to WordPress: {str(e)}", exc_info=True)
        return False, None, str(e)


def _publish_to_strapi(content_obj, cms_provider, scheduled_at=None):
    """
    Helper function to publish content to Strapi
    Assumes a collection endpoint (default: /api/articles) and bearer token auth
    """
    try:
        settings = cms_provider.settings
        api_url = settings.get('api_url')
        token = settings.get('token')
        collection = settings.get('collection', '/api/articles')

        if not api_url or not token:
            return False, None, "Strapi settings incomplete"

        if not api_url.endswith('/'):
            api_url += '/'

        endpoint = api_url.rstrip('/') + collection

        # Strapi collection in this environment expects Title/Content (case-sensitive)
        payload = {
            "data": {
                "Title": content_obj.title,
                "Content": content_obj.content_html or content_obj.title,
            }
        }

        # For immediate publish, set publishedAt to now (or scheduled time if provided)
        if scheduled_at and scheduled_at > django_timezone.now():
            payload["data"]["publishedAt"] = scheduled_at.isoformat()
        else:
            payload["data"]["publishedAt"] = django_timezone.now().isoformat()

        resp = requests.post(
            endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=30,
        )

        if not resp.ok:
            try:
                err_json = resp.json()
                msg = err_json.get('error', {}).get('message') or str(err_json)
            except Exception:
                msg = resp.text
            return False, None, f"Strapi API error: {msg}"

        return True, resp.json(), None

    except Exception as e:
        logger.error(f"Error publishing to Strapi: {str(e)}", exc_info=True)
        return False, None, str(e)


def _html_to_contentful_rich_text(html_content: str):
    """
    Very lightweight HTML -> Contentful Rich Text converter.
    - Strips tags and wraps into a single paragraph with a text node.
    - Keeps plain text only; does not preserve formatting/links.
    If richer mapping is needed, plug in a real HTML-to-rich-text converter.
    """
    import re

    if not html_content:
        return {
            "nodeType": "document",
            "data": {},
            "content": []
        }

    # Strip HTML tags to plain text
    plain = re.sub(r'<[^>]+>', '', html_content)
    plain = plain.strip()

    return {
        "nodeType": "document",
        "data": {},
        "content": [
            {
                "nodeType": "paragraph",
                "data": {},
                "content": [
                    {
                        "nodeType": "text",
                        "value": plain,
                        "marks": [],
                        "data": {}
                    }
                ]
            }
        ]
    }


def _publish_to_contentful(content_obj, cms_provider):
    """
    Helper function to publish content to Contentful via CMA
    Steps:
      1) Create entry with fields
      2) Publish entry using the returned version
    """
    try:
        settings = cms_provider.settings
        api_url = settings.get('api_url') or 'https://api.contentful.com'
        management_token = settings.get('management_token')
        space_id = settings.get('space_id')
        environment_id = settings.get('environment_id') or 'master'
        content_type_id = settings.get('content_type_id')

        if not all([management_token, space_id, environment_id, content_type_id]):
            return False, None, "Contentful settings incomplete (token, space_id, environment_id, content_type_id required)"

        if not api_url.endswith('/'):
            api_url += '/'
        base = api_url.rstrip('/')

        create_endpoint = f"{base}/spaces/{space_id}/environments/{environment_id}/entries"
        rich_body = _html_to_contentful_rich_text(content_obj.content_html or content_obj.title)
        fields_payload = {
            "fields": {
                "title": {"en-US": content_obj.title},
                "body": {"en-US": rich_body},
            }
        }

        create_resp = requests.post(
            create_endpoint,
            json=fields_payload,
            headers={
                "Authorization": f"Bearer {management_token}",
                "Content-Type": "application/vnd.contentful.management.v1+json",
                "X-Contentful-Content-Type": content_type_id,
            },
            timeout=30,
        )

        if not create_resp.ok:
            try:
                err_json = create_resp.json()
                msg = err_json.get('message') or str(err_json)
            except Exception:
                msg = create_resp.text
            return False, None, f"Contentful create error: {msg}"

        entry_data = create_resp.json()
        entry_id = entry_data.get('sys', {}).get('id')
        entry_version = entry_data.get('sys', {}).get('version')

        if not entry_id or entry_version is None:
            return False, None, "Contentful create response missing entry id/version"

        publish_endpoint = f"{base}/spaces/{space_id}/environments/{environment_id}/entries/{entry_id}/published"
        publish_resp = requests.put(
            publish_endpoint,
            headers={
                "Authorization": f"Bearer {management_token}",
                "X-Contentful-Version": str(entry_version),
            },
            timeout=30,
        )

        if not publish_resp.ok:
            try:
                err_json = publish_resp.json()
                msg = err_json.get('message') or str(err_json)
            except Exception:
                msg = publish_resp.text
            return False, None, f"Contentful publish error: {msg}"

        return True, {
            "entry": entry_data,
            "publish": publish_resp.json()
        }, None

    except Exception as e:
        logger.error(f"Error publishing to Contentful: {str(e)}", exc_info=True)
        return False, None, str(e)


def _publish_to_joomla(content_obj, cms_provider):
    """
    Helper function to publish content to Joomla 4/5 via core API
    Expects:
      - settings.api_url: base site URL (no trailing slash)
      - settings.endpoint: default /api/index.php/v1/content/articles
      - settings.token: API token for Bearer auth
      - settings.catid: category id to post into
      - settings.state: article state (1=published, 0=unpublished)
    """
    try:
        settings = cms_provider.settings
        api_url = settings.get('api_url')
        token = settings.get('token')
        endpoint_path = settings.get('endpoint', '/api/index.php/v1/content/articles')
        catid = settings.get('catid')
        state = settings.get('state', 1)

        if not api_url or not token or not catid:
            return False, None, "Joomla settings incomplete (api_url, token, catid required)"

        if not api_url.endswith('/'):
            api_url += '/'
        endpoint = api_url.rstrip('/') + endpoint_path

        payload = {
            "title": content_obj.title,
            "catid": catid,
            "state": state,
            "introtext": content_obj.content_html or content_obj.title,
            "fulltext": content_obj.content_html or "",
            "language": "*",
            "access": 1,
        }

        resp = requests.post(
            endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=30,
        )

        if not resp.ok:
            try:
                err_json = resp.json()
                msg = err_json.get('message') or str(err_json)
            except Exception:
                msg = resp.text
            return False, None, f"Joomla API error: {msg}"

        return True, resp.json(), None
    except Exception as e:
        logger.error(f"Error publishing to Joomla: {str(e)}", exc_info=True)
        return False, None, str(e)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_content(request):
    """
    Publish content to CMS provider (with scheduling support)
    
    Request body:
    {
        "content_id": int,
        "cms_provider_id": int,
        "publish_now": bool,
        "scheduled_at": "2025-12-10T00:00:00Z" (optional if publish_now is True)
    }
    """
    try:
        serializer = PublishContentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        content_id = data['content_id']
        cms_provider_id = data['cms_provider_id']
        publish_now = data.get('publish_now', False)
        scheduled_at = data.get('scheduled_at')
        
        # Fetch and validate content
        content_obj = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )
        
        # Fetch and validate CMS provider
        cms_provider = get_object_or_404(
            CMSProvider,
            id=cms_provider_id,
            domain=content_obj.domain,
            is_active=True
        )
        
        if publish_now:
            # Publish immediately
            if cms_provider.provider_type == 'wordpress':
                success, pub_result, error = _publish_to_wordpress(content_obj, cms_provider)
            elif cms_provider.provider_type == 'strapi':
                success, pub_result, error = _publish_to_strapi(content_obj, cms_provider)
            elif cms_provider.provider_type == 'joomla':
                success, pub_result, error = _publish_to_joomla(content_obj, cms_provider)
            elif cms_provider.provider_type == 'contentful':
                success, pub_result, error = _publish_to_contentful(content_obj, cms_provider)
            else:
                return Response({
                    'status': 'error',
                    'message': f'Provider type {cms_provider.provider_type} not yet supported for publishing'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not success:
                return Response({
                    'status': 'error',
                    'message': error
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Update content status
            content_obj.status = 'published'
            content_obj.published_date = django_timezone.now()
            content_obj.save(update_fields=['status', 'published_date', 'modified_at'])
            
            return Response({
                'status': 'success',
                'message': 'Published successfully',
                'provider_response': pub_result,
            })
        else:
            # Schedule for later
            if cms_provider.provider_type in ['joomla', 'contentful']:
                return Response({
                    'status': 'error',
                    'message': f'Scheduling is not yet supported for {cms_provider.provider_type} publishing'
                }, status=status.HTTP_400_BAD_REQUEST)
            if not scheduled_at:
                return Response({
                    'status': 'error',
                    'message': 'scheduled_at is required when publish_now is False'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate scheduled time is in the future
            if scheduled_at <= django_timezone.now():
                return Response({
                    'status': 'error',
                    'message': 'scheduled_at must be in the future'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Reuse existing scheduled publication if one already exists for this content
            scheduled_pub = ScheduledPublication.objects.filter(
                content=content_obj,
                status__in=['scheduled', 'publishing']
            ).order_by('-created_at').first()

            if scheduled_pub:
                # Update existing schedule
                scheduled_pub.cms_provider = cms_provider
                scheduled_pub.scheduled_at = scheduled_at
                scheduled_pub.status = 'scheduled'
                scheduled_pub.error_message = None
                scheduled_pub.save(update_fields=[
                    'cms_provider', 'scheduled_at', 'status', 'error_message', 'modified_at'
                ])
            else:
                # Create new schedule
                scheduled_pub = ScheduledPublication.objects.create(
                    content=content_obj,
                    cms_provider=cms_provider,
                    scheduled_at=scheduled_at,
                    status='scheduled'
                )
            
            # Update content scheduled_date and status
            content_obj.scheduled_date = scheduled_at
            content_obj.status = 'scheduled'
            content_obj.save(update_fields=['scheduled_date', 'status', 'modified_at'])
            
            return Response({
                'status': 'success',
                'message': 'Content scheduled for publication',
                'scheduled_publication_id': scheduled_pub.id,
                'scheduled_at': scheduled_at.isoformat(),
            })
            
    except Http404:
        return Response({
            'status': 'error',
            'message': 'Content or CMS provider not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error publishing content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error publishing content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_generated_content(request, content_id):
    """
    Delete a generated content
    """
    try:
        content = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )

        content.delete()

        return Response({
            'status': 'success',
            'message': 'Content deleted successfully'
        }, status=status.HTTP_200_OK)

    except Http404:
        return Response({
            'status': 'error',
            'message': 'Generated content not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting generated content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error deleting generated content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# CMS Provider Management Endpoints

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def cms_provider_list(request):
    """
    List CMS providers for domains in user's organization or create a new one
    """
    if request.method == 'GET':
        domain_id = request.query_params.get('domain_id')
        
        if domain_id:
            # Get providers for specific domain
            domain = get_object_or_404(
                Domain,
                id=domain_id,
                organisation=request.user.organisation
            )
            providers = CMSProvider.objects.filter(domain=domain)
        else:
            # Get all providers for user's organization
            domain_ids = Domain.objects.filter(
                organisation=request.user.organisation
            ).values_list('id', flat=True)
            providers = CMSProvider.objects.filter(domain_id__in=domain_ids)
        
        serializer = CMSProviderSerializer(providers, many=True)
        return Response({
            'status': 'success',
            'results': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = CMSProviderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate domain belongs to user's organization
        domain = serializer.validated_data['domain']
        if domain.organisation != request.user.organisation:
            return Response({
                'status': 'error',
                'message': 'Domain does not belong to your organization'
            }, status=status.HTTP_403_FORBIDDEN)
        
        provider = serializer.save()
        return Response({
            'status': 'success',
            'message': 'CMS provider created successfully',
            'data': CMSProviderSerializer(provider).data
        }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def cms_provider_detail(request, provider_id):
    """
    Get, update, or delete a specific CMS provider
    """
    provider = get_object_or_404(CMSProvider, id=provider_id)
    
    # Validate ownership
    if provider.domain.organisation != request.user.organisation:
        return Response({
            'status': 'error',
            'message': 'CMS provider does not belong to your organization'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        serializer = CMSProviderSerializer(provider)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    
    elif request.method == 'PUT':
        serializer = CMSProviderCreateSerializer(provider, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate domain if being changed
        if 'domain' in serializer.validated_data:
            new_domain = serializer.validated_data['domain']
            if new_domain.organisation != request.user.organisation:
                return Response({
                    'status': 'error',
                    'message': 'Domain does not belong to your organization'
                }, status=status.HTTP_403_FORBIDDEN)
        
        provider = serializer.save()
        return Response({
            'status': 'success',
            'message': 'CMS provider updated successfully',
            'data': CMSProviderSerializer(provider).data
        })
    
    elif request.method == 'DELETE':
        provider.delete()
        return Response({
            'status': 'success',
            'message': 'CMS provider deleted successfully'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_cms_provider_connection(request, provider_id):
    """
    Test connection to a CMS provider
    """
    provider = get_object_or_404(CMSProvider, id=provider_id)
    
    # Validate ownership
    if provider.domain.organisation != request.user.organisation:
        return Response({
            'status': 'error',
            'message': 'CMS provider does not belong to your organization'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if provider.provider_type == 'wordpress':
        try:
            settings = provider.settings
            wp_api_url = settings.get('api_url')
            wp_username = settings.get('username')
            wp_app_password = settings.get('app_password')
            
            if not wp_api_url or not wp_username or not wp_app_password:
                return Response({
                    'status': 'error',
                    'message': 'WordPress settings incomplete'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Test connection by fetching user info
            if not wp_api_url.endswith('/'):
                wp_api_url += '/'
            test_url = f"{wp_api_url}users/me"
            
            resp = requests.get(
                test_url,
                auth=(wp_username, wp_app_password),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            
            if resp.ok:
                user_data = resp.json()
                return Response({
                    'status': 'success',
                    'message': 'Connection successful',
                    'data': {
                        'username': user_data.get('name', wp_username),
                        'site_url': settings.get('site_url', wp_api_url)
                    }
                })
            else:
                return Response({
                    'status': 'error',
                    'message': f'Connection failed: {resp.text}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error testing WordPress connection: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': f'Connection test failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({
            'status': 'error',
            'message': f'Provider type {provider.provider_type} not supported for testing'
        }, status=status.HTTP_400_BAD_REQUEST)


def _strip_html_tags(html_content: str) -> str:
    """Strip HTML tags from content and return plain text"""
    if not html_content:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', html_content)
    # Remove extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_ai_content(request):
    """
    Detect if content is AI-generated using Hugging Face API

    Expected request body:
    {
        "text": str (plain text or HTML content to analyze),
        "content_id": int (optional - if provided, saves the result to the content record)
    }

    Returns:
    {
        "status": "success",
        "ai_score": float (0-100, higher = more likely AI-generated),
        "human_score": float (0-100, higher = more likely human-written),
        "label": str ("AI-generated" or "Human-written"),
        "confidence": float (0-100),
        "checked_at": str (ISO timestamp, only if content_id provided)
    }
    """
    try:
        text = request.data.get('text', '')
        content_id = request.data.get('content_id')

        if not text:
            return Response({
                'status': 'error',
                'message': 'Text is required for AI detection'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Strip HTML tags if present
        plain_text = _strip_html_tags(text)

        if len(plain_text) < 50:
            return Response({
                'status': 'error',
                'message': 'Text must be at least 50 characters for accurate detection'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Truncate to ~1500 characters (RoBERTa has 514 token limit, ~3 chars per token)
        if len(plain_text) > 1500:
            plain_text = plain_text[:1500]

        # Get Hugging Face API key from settings
        hf_api_key = config('HUGGINGFACE_API_KEY', default='')

        if not hf_api_key:
            return Response({
                'status': 'error',
                'message': 'Hugging Face API key not configured. Please add HUGGINGFACE_API_KEY to your environment.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Call Hugging Face Inference API with ChatGPT detector model (more accurate for modern AI)
        api_url = "https://router.huggingface.co/hf-inference/models/Hello-SimpleAI/chatgpt-detector-roberta"

        headers = {
            "Authorization": f"Bearer {hf_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": plain_text
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=30)

        if response.status_code == 503:
            # Model is loading
            return Response({
                'status': 'loading',
                'message': 'AI detection model is loading. Please try again in a few seconds.',
                'estimated_time': response.json().get('estimated_time', 20)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not response.ok:
            logger.error(f"Hugging Face API error: {response.status_code} - {response.text}")
            return Response({
                'status': 'error',
                'message': f'AI detection service error: {response.text}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        result = response.json()

        # Parse the response - roberta-base-openai-detector returns classifications
        # Example: [[{"label": "Fake", "score": 0.9}, {"label": "Real", "score": 0.1}]]
        if isinstance(result, list) and len(result) > 0:
            classifications = result[0] if isinstance(result[0], list) else result

            ai_score = 0
            human_score = 0

            for item in classifications:
                label = item.get('label', '').lower()
                score = item.get('score', 0) * 100

                # Handle different model label formats
                if label in ['fake', 'chatgpt', 'ai', 'gpt']:  # AI-generated labels
                    ai_score = score
                elif label in ['real', 'human']:  # Human-written labels
                    human_score = score

            # Determine label and confidence
            if ai_score > human_score:
                label = "AI-generated"
                confidence = ai_score
            else:
                label = "Human-written"
                confidence = human_score

            checked_at = None
            # Save results to database if content_id is provided
            if content_id:
                try:
                    content_obj = GeneratedContent.objects.get(
                        id=content_id,
                        domain__organisation=request.user.organisation
                    )
                    content_obj.ai_detection_score = round(ai_score, 2)
                    content_obj.human_detection_score = round(human_score, 2)
                    content_obj.ai_detection_label = label
                    content_obj.ai_detection_checked_at = timezone.now()
                    content_obj.save(update_fields=[
                        'ai_detection_score', 'human_detection_score',
                        'ai_detection_label', 'ai_detection_checked_at'
                    ])
                    checked_at = content_obj.ai_detection_checked_at.isoformat()
                    logger.info(f"AI detection results saved for content {content_id}")
                except GeneratedContent.DoesNotExist:
                    logger.warning(f"Content {content_id} not found for AI detection save")

            response_data = {
                'status': 'success',
                'ai_score': round(ai_score, 1),
                'human_score': round(human_score, 1),
                'label': label,
                'confidence': round(confidence, 1),
                'text_analyzed_length': len(plain_text)
            }
            if checked_at:
                response_data['checked_at'] = checked_at

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.error(f"Unexpected response format from Hugging Face: {result}")
            return Response({
                'status': 'error',
                'message': 'Unexpected response from AI detection service'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except requests.exceptions.Timeout:
        return Response({
            'status': 'error',
            'message': 'AI detection service timed out. Please try again.'
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        logger.error(f"Error detecting AI content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error detecting AI content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# Content Review Endpoints
# ============================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def content_comments(request, content_id):
    """
    GET: Get all comments for a content
    POST: Add a new comment on selected text
    """
    # Verify content exists and user has access
    try:
        content = GeneratedContent.objects.get(id=content_id)
        # Verify user has access to this domain
        if content.domain.organisation != request.user.organisation:
            return Response({
                'status': 'error',
                'message': 'You do not have access to this content'
            }, status=status.HTTP_403_FORBIDDEN)
    except GeneratedContent.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Content not found'
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        comments = ContentComment.objects.filter(content=content)
        serializer = ContentCommentSerializer(comments, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data,
            'total': comments.count(),
            'pending': comments.filter(status='pending').count()
        })

    elif request.method == 'POST':
        serializer = CreateContentCommentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Create new comment
        comment = ContentComment.objects.create(
            content=content,
            author=request.user,
            selected_text=data['selected_text'],
            comment=data['comment'],
            suggestion=data.get('suggestion', ''),
            status='pending'
        )
        response_serializer = ContentCommentSerializer(comment)
        return Response({
            'status': 'success',
            'message': 'Comment added',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def content_comment_detail(request, content_id, comment_id):
    """
    GET: Get a specific comment
    PATCH: Update comment or resolve (accept/reject)
    DELETE: Delete a comment (only by author)
    """
    try:
        comment = ContentComment.objects.get(id=comment_id, content_id=content_id)
        # Verify user has access
        if comment.content.domain.organisation != request.user.organisation:
            return Response({
                'status': 'error',
                'message': 'You do not have access to this comment'
            }, status=status.HTTP_403_FORBIDDEN)
    except ContentComment.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Comment not found'
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ContentCommentSerializer(comment)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    elif request.method == 'PATCH':
        # Check what action is being performed
        new_status = request.data.get('status')

        if new_status in ['accepted', 'rejected']:
            # Resolving a comment - anyone in the org can do this
            comment.status = new_status
            comment.resolved_by = request.user
            comment.resolved_at = timezone.now()
            comment.save()

            serializer = ContentCommentSerializer(comment)
            return Response({
                'status': 'success',
                'message': f'Comment {new_status}',
                'data': serializer.data
            })

        # Updating comment text - only author can do this
        if comment.author != request.user:
            return Response({
                'status': 'error',
                'message': 'Only the author can edit this comment'
            }, status=status.HTTP_403_FORBIDDEN)

        if 'comment' in request.data:
            comment.comment = request.data['comment']
        if 'suggestion' in request.data:
            comment.suggestion = request.data['suggestion']
        comment.save()

        serializer = ContentCommentSerializer(comment)
        return Response({
            'status': 'success',
            'message': 'Comment updated',
            'data': serializer.data
        })

    elif request.method == 'DELETE':
        # Only author can delete their comment
        if comment.author != request.user:
            return Response({
                'status': 'error',
                'message': 'Only the author can delete this comment'
            }, status=status.HTTP_403_FORBIDDEN)

        comment.delete()
        return Response({
            'status': 'success',
            'message': 'Comment deleted'
        }, status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Bulk Content Upload — Value Maps, Views, and Queue Engine
# =============================================================================

# Maps (Content Category, Content Type) display names → article_type DB code
BULK_CONTENT_TYPE_MAP = {
    ('Articles', 'Blog Post'): 'blog',
    ('Articles', 'How-to Guide'): 'guide',
    ('Articles', 'Comparison Article'): 'comparison',
    ('Articles', 'Listicle'): 'listicle',
    ('Articles', 'Technical Article'): 'technical',
    ('Web Pages', 'Landing Page'): 'landing_page',
    ('Web Pages', 'Services Page'): 'services_page',
    ('Web Pages', 'Product Page'): 'product_page',
    ('Web Pages', 'Features Page'): 'features_page',
    ('Web Pages', 'Resource/Guide Page'): 'resource_page',
    ('Social Media', 'Twitter/X Post'): 'twitter_post',
    ('Social Media', 'LinkedIn Post'): 'linkedin_post',
    ('Social Media', 'Facebook Post'): 'facebook_post',
    ('Social Media', 'Instagram Caption'): 'instagram_caption',
    ('Social Media', 'Thread/Carousel'): 'social_thread',
    ('Community', 'Reddit Post'): 'reddit_post',
    ('Community', 'Quora Answer'): 'quora_answer',
    ('Community', 'Forum Post'): 'forum_post',
    ('Community', 'Product Hunt Launch'): 'product_hunt',
    ('Community', 'Newsletter Snippet'): 'newsletter_snippet',
}

BULK_COUNTRY_MAP = {
    'United States': 'united_states',
    'United Kingdom': 'united_kingdom',
    'Canada': 'canada',
    'Australia': 'australia',
    'Germany': 'germany',
    'France': 'france',
    'Spain': 'spain',
    'Italy': 'italy',
    'Netherlands': 'netherlands',
    'Sweden': 'sweden',
    'Norway': 'norway',
    'Denmark': 'denmark',
    'Finland': 'finland',
    'Switzerland': 'switzerland',
    'Austria': 'austria',
    'Belgium': 'belgium',
    'Ireland': 'ireland',
    'Portugal': 'portugal',
    'Poland': 'poland',
    'India': 'india',
    'Singapore': 'singapore',
    'Japan': 'japan',
    'South Korea': 'south_korea',
    'China': 'china',
    'Brazil': 'brazil',
    'Mexico': 'mexico',
    'Argentina': 'argentina',
    'South Africa': 'south_africa',
    'UAE': 'uae',
    'Saudi Arabia': 'saudi_arabia',
    'Global': 'global',
}

BULK_LANGUAGE_MAP = {
    'US English': 'us_english',
    'UK English': 'uk_english',
    'Australian English': 'australian_english',
    'Canadian English': 'canadian_english',
    'Indian English': 'indian_english',
    'Irish English': 'irish_english',
    'South African English': 'south_african_english',
    'New Zealand English': 'new_zealand_english',
    'Singapore English': 'singapore_english',
}

BULK_AUDIENCE_MAP = {
    'General': 'general',
    'Beginners': 'beginners',
    'Professionals': 'professionals',
    'Experts': 'experts',
}

BULK_PRIORITY_MAP = {
    'High': 'high',
    'Medium': 'medium',
    'Low': 'low',
}

# Valid manual status transitions for bulk upload items
BULK_VALID_STATUS_TRANSITIONS = {
    'generated': ['in_review'],
    'in_review': ['approved'],
}

# Excel template column order (0-indexed)
BULK_EXCEL_COLUMNS = [
    'Content Category',             # 0 (A)
    'Content Type',                 # 1 (B)
    'Title / Page Title / Topic',   # 2 (C)
    'Keywords / Hashtags / Tags',   # 3 (D)
    'Target Country',               # 4 (E)
    'Target Language',              # 5 (F)
    'Target Audience',              # 6 (G)
    'Word Count',                   # 7 (H)
    'Tone of Voice',                # 8 (I)
    'Content Style',                # 9 (J)
    'Key Messages',                 # 10 (K)
    'Topics to Avoid',              # 11 (L)
    'Additional Instructions',      # 12 (M)
    'Reference URLs',               # 13 (N)
    'Reference Descriptions',       # 14 (O)
    'Priority',                     # 15 (P)
]


def _run_bulk_generation_queue(batch_id):
    """
    Background thread: processes all 'processed' items in a batch ONE BY ONE.
    Each item failure is isolated — does not stop the queue.

    Django DB connections are per-thread. We must close the connection
    when the thread finishes to prevent connection leaks.
    """
    try:
        batch = BulkUploadBatch.objects.get(id=batch_id)
        items = BulkUploadItem.objects.filter(
            batch=batch,
            status='processed'
        ).order_by('row_number')

        generator = ClaudeContentGenerator()
        # Per-batch URL cache so identical reference URLs across rows are
        # fetched once rather than once per row.
        url_fetch_cache = {}

        for item in items:
            try:
                # Mark as generating
                item.status = 'generating'
                item.generation_started_at = timezone.now()
                item.save(update_fields=['status', 'generation_started_at', 'modified_at'])

                # Parse reference URLs into references list
                references = []
                if item.reference_urls:
                    urls = [u.strip() for u in item.reference_urls.split('|') if u.strip()]
                    descs = [d.strip() for d in item.reference_descriptions.split('|')] if item.reference_descriptions else []
                    for i, url in enumerate(urls):
                        references.append({
                            'type': 'article',
                            'url': url,
                            'description': descs[i] if i < len(descs) else '',
                        })

                # Build generation params (same structure as generate_content view)
                generation_params = {
                    'title': item.title,
                    'keywords': item.keywords,
                    'article_type': item.article_type,
                    'target_country': item.target_country,
                    'target_language': item.target_language,
                    'references': references,
                    'tone': item.tone or 'professional',
                    'style': item.style or 'informative',
                    'goal': 'educate',
                    'audience': item.target_audience or 'general',
                    'depth': 'comprehensive',
                    'word_count': item.word_count or 1500,
                    'source_reference': '',
                    'key_messages': item.key_messages or '',
                    'topics_to_avoid': item.topics_to_avoid or '',
                    'additional_instructions': item.additional_instructions or '',
                    'brand_values': '',
                }

                # Enrich reference URLs with actual fetched content to prevent hallucination.
                # The per-batch cache avoids re-fetching the same URL for multiple rows.
                if generation_params.get('references'):
                    generation_params['references'] = _enrich_references_with_content(
                        generation_params['references'], cache=url_fetch_cache
                    )

                # Generate content using 2-step process for better structure:
                # Step 1: Generate outline, Step 2: Generate from outline
                # This ensures the content follows a logical flow (Issue 11)
                logger.info(f"Bulk item {item.id} (row {item.row_number}): generating outline for '{item.title}'")
                try:
                    outline_result = generator.generate_outline(generation_params)
                    outline = outline_result.get('outline', [])
                    if outline:
                        logger.info(f"Bulk item {item.id}: generating content from {len(outline)}-section outline")
                        generation_result = generator.generate_content_from_outline(generation_params, outline)
                    else:
                        logger.info(f"Bulk item {item.id}: outline empty, falling back to direct generation")
                        generation_result = generator.generate_content(generation_params)
                except Exception as outline_err:
                    logger.warning(
                        f"Bulk item {item.id}: outline generation failed ({outline_err}), "
                        f"falling back to direct generation"
                    )
                    generation_result = generator.generate_content(generation_params)

                # Generate SEO meta tags (separate lightweight call)
                meta_result = generator.generate_meta_tags(
                    title=item.title,
                    content_html=generation_result['content_html'],
                    keywords=item.keywords,
                )

                # Create GeneratedContent record (same pattern as generate_content view)
                generated_content = GeneratedContent.objects.create(
                    domain=batch.domain,
                    title=item.title,
                    content_html=generation_result['content_html'],
                    meta_title=meta_result['meta_title'],
                    meta_description=meta_result['meta_description'],
                    source_type='manual',
                    source_id=batch.id,
                    source_reference=f'Bulk Upload Batch #{batch.id}',
                    article_type=item.article_type,
                    keywords=item.keywords,
                    tone=item.tone or 'professional',
                    style=item.style or 'informative',
                    goal='educate',
                    audience=item.target_audience or 'general',
                    depth='comprehensive',
                    word_count=item.word_count or 1500,
                    actual_word_count=generation_result['actual_word_count'],
                    status='generated',
                    priority=item.priority or 'medium',
                    model_used=generation_result['model_used'],
                    generation_time_seconds=generation_result['generation_time_seconds'],
                    prompt_tokens=generation_result['prompt_tokens'],
                    completion_tokens=generation_result['completion_tokens'],
                )

                # Update item
                item.status = 'generated'
                item.generated_content = generated_content
                item.generation_completed_at = timezone.now()
                item.error_message = None
                item.save(update_fields=[
                    'status', 'generated_content', 'generation_completed_at',
                    'error_message', 'modified_at'
                ])

                # Update batch counters
                batch.refresh_from_db()
                batch.processed_items += 1
                batch.successful_items += 1
                batch.save(update_fields=['processed_items', 'successful_items'])

                logger.info(
                    f"Bulk item {item.id} (row {item.row_number}) generated successfully "
                    f"-> GeneratedContent {generated_content.id}"
                )

            except Exception as e:
                logger.error(
                    f"Bulk item {item.id} (row {item.row_number}) failed: {str(e)}",
                    exc_info=True
                )
                item.status = 'generation_failed'
                item.error_message = str(e)[:2000]
                item.generation_completed_at = timezone.now()
                item.save(update_fields=[
                    'status', 'error_message', 'generation_completed_at', 'modified_at'
                ])

                batch.refresh_from_db()
                batch.processed_items += 1
                batch.failed_items += 1
                batch.save(update_fields=['processed_items', 'failed_items'])

        # All items processed — update batch status
        batch.refresh_from_db()
        batch.completed_at = timezone.now()
        if batch.failed_items == 0:
            batch.status = 'completed'
        elif batch.successful_items == 0:
            batch.status = 'failed'
        else:
            batch.status = 'completed_with_errors'
        batch.save(update_fields=['status', 'completed_at'])

        logger.info(
            f"Bulk batch {batch_id} completed: "
            f"{batch.successful_items} success, {batch.failed_items} failed"
        )

    except Exception as e:
        logger.error(
            f"Bulk generation queue fatal error for batch {batch_id}: {str(e)}",
            exc_info=True
        )
        try:
            batch = BulkUploadBatch.objects.get(id=batch_id)
            batch.status = 'failed'
            batch.error_message = str(e)[:2000]
            batch.completed_at = timezone.now()
            batch.save(update_fields=['status', 'error_message', 'completed_at'])
        except Exception:
            pass
    finally:
        connection.close()


def _run_single_item_generation(item_id):
    """
    Background thread for retrying a single failed item.
    Same logic as the inner loop of _run_bulk_generation_queue.
    """
    try:
        item = BulkUploadItem.objects.select_related('batch', 'batch__domain').get(id=item_id)
        batch = item.batch

        item.status = 'generating'
        item.generation_started_at = timezone.now()
        item.save(update_fields=['status', 'generation_started_at', 'modified_at'])

        # Parse references
        references = []
        if item.reference_urls:
            urls = [u.strip() for u in item.reference_urls.split('|') if u.strip()]
            descs = [d.strip() for d in item.reference_descriptions.split('|')] if item.reference_descriptions else []
            for i, url in enumerate(urls):
                references.append({
                    'type': 'article',
                    'url': url,
                    'description': descs[i] if i < len(descs) else '',
                })

        generation_params = {
            'title': item.title,
            'keywords': item.keywords,
            'article_type': item.article_type,
            'target_country': item.target_country,
            'target_language': item.target_language,
            'references': references,
            'tone': item.tone or 'professional',
            'style': item.style or 'informative',
            'goal': 'educate',
            'audience': item.target_audience or 'general',
            'depth': 'comprehensive',
            'word_count': item.word_count or 1500,
            'source_reference': '',
            'key_messages': item.key_messages or '',
            'topics_to_avoid': item.topics_to_avoid or '',
            'additional_instructions': item.additional_instructions or '',
            'brand_values': '',
        }

        # Enrich reference URLs with actual fetched content to prevent hallucination.
        # (The original batch path already does this; the retry path was missing it.)
        if generation_params.get('references'):
            generation_params['references'] = _enrich_references_with_content(generation_params['references'])

        generator = ClaudeContentGenerator()
        generation_result = generator.generate_content(generation_params)

        # Generate SEO meta tags
        meta_result = generator.generate_meta_tags(
            title=item.title,
            content_html=generation_result['content_html'],
            keywords=item.keywords,
        )

        generated_content = GeneratedContent.objects.create(
            domain=batch.domain,
            title=item.title,
            content_html=generation_result['content_html'],
            source_type='manual',
            source_id=batch.id,
            source_reference=f'Bulk Upload Batch #{batch.id}',
            article_type=item.article_type,
            keywords=item.keywords,
            tone=item.tone or 'professional',
            style=item.style or 'informative',
            goal='educate',
            audience=item.target_audience or 'general',
            depth='comprehensive',
            word_count=item.word_count or 1500,
            actual_word_count=generation_result['actual_word_count'],
            status='generated',
            priority=item.priority or 'medium',
            model_used=generation_result['model_used'],
            generation_time_seconds=generation_result['generation_time_seconds'],
            prompt_tokens=generation_result['prompt_tokens'],
            completion_tokens=generation_result['completion_tokens'],
            meta_title=meta_result['meta_title'],
            meta_description=meta_result['meta_description'],
        )

        item.status = 'generated'
        item.generated_content = generated_content
        item.generation_completed_at = timezone.now()
        item.error_message = None
        item.save(update_fields=[
            'status', 'generated_content', 'generation_completed_at',
            'error_message', 'modified_at'
        ])

        # Update batch counters (was previously failed, now succeeded)
        batch.refresh_from_db()
        batch.successful_items += 1
        batch.failed_items = max(0, batch.failed_items - 1)
        if batch.failed_items == 0 and batch.status == 'completed_with_errors':
            batch.status = 'completed'
        batch.save(update_fields=['successful_items', 'failed_items', 'status'])

        logger.info(f"Bulk item {item_id} retry succeeded -> GeneratedContent {generated_content.id}")

    except Exception as e:
        logger.error(f"Bulk item {item_id} retry failed: {str(e)}", exc_info=True)
        try:
            item = BulkUploadItem.objects.get(id=item_id)
            item.status = 'generation_failed'
            item.error_message = str(e)[:2000]
            item.generation_completed_at = timezone.now()
            item.save(update_fields=[
                'status', 'error_message', 'generation_completed_at', 'modified_at'
            ])
        except Exception:
            pass
    finally:
        connection.close()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_bulk_upload_template(request):
    """
    Download the .xlsx template with dropdown-validated columns.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter
    from openpyxl.workbook.defined_name import DefinedName
    from io import BytesIO
    from django.http import HttpResponse

    wb = openpyxl.Workbook()

    # ── Main sheet ────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Bulk Upload"

    headers = BULK_EXCEL_COLUMNS
    header_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    col_widths = [20, 25, 45, 40, 20, 22, 18, 14, 20, 20, 35, 35, 40, 45, 45, 12]

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = col_widths[col_idx - 1]

    ws.row_dimensions[1].height = 35
    ws.freeze_panes = "A2"

    # ── Lookup sheet (hidden) ─────────────────────────────────────────
    ws_lookup = wb.create_sheet("_Lookup")
    ws_lookup.sheet_state = "hidden"

    content_categories = ['Articles', 'Web Pages', 'Social Media', 'Community']
    content_types_by_cat = {
        'Articles': ['Blog Post', 'How-to Guide', 'Comparison Article', 'Listicle', 'Technical Article'],
        'Web Pages': ['Landing Page', 'Services Page', 'Product Page', 'Features Page', 'Resource/Guide Page'],
        'Social Media': ['Twitter/X Post', 'LinkedIn Post', 'Facebook Post', 'Instagram Caption', 'Thread/Carousel'],
        'Community': ['Reddit Post', 'Quora Answer', 'Forum Post', 'Product Hunt Launch', 'Newsletter Snippet'],
    }
    countries = list(BULK_COUNTRY_MAP.keys())
    languages = list(BULK_LANGUAGE_MAP.keys())
    audiences = list(BULK_AUDIENCE_MAP.keys())
    priorities = list(BULK_PRIORITY_MAP.keys())
    word_counts = ['50', '150', '300', '400', '500', '800', '1500', '2000', '2500', '3500']

    # Col A: Content Categories
    ws_lookup.cell(row=1, column=1, value="Content Category")
    for i, cat in enumerate(content_categories, start=2):
        ws_lookup.cell(row=i, column=1, value=cat)

    # Col B-E: Content Types per category
    for cat_idx, (category, types) in enumerate(content_types_by_cat.items()):
        col = 2 + cat_idx
        ws_lookup.cell(row=1, column=col, value=category)
        for i, ctype in enumerate(types, start=2):
            ws_lookup.cell(row=i, column=col, value=ctype)

    # Col G: Countries
    ws_lookup.cell(row=1, column=7, value="Country")
    for i, c in enumerate(countries, start=2):
        ws_lookup.cell(row=i, column=7, value=c)

    # Col H: Languages
    ws_lookup.cell(row=1, column=8, value="Language")
    for i, l in enumerate(languages, start=2):
        ws_lookup.cell(row=i, column=8, value=l)

    # Col I: Audiences
    ws_lookup.cell(row=1, column=9, value="Audience")
    for i, a in enumerate(audiences, start=2):
        ws_lookup.cell(row=i, column=9, value=a)

    # Col J: Word Counts
    ws_lookup.cell(row=1, column=10, value="Word Count")
    for i, wc in enumerate(word_counts, start=2):
        ws_lookup.cell(row=i, column=10, value=int(wc))

    # Col K: Priorities
    ws_lookup.cell(row=1, column=11, value="Priority")
    for i, p in enumerate(priorities, start=2):
        ws_lookup.cell(row=i, column=11, value=p)

    # ── Named Ranges ──────────────────────────────────────────────────
    wb.defined_names.add(DefinedName(
        name="ContentCategories",
        attr_text=f"'_Lookup'!$A$2:$A${1 + len(content_categories)}"
    ))

    cat_range_names = {
        'Articles': 'Articles',
        'Web Pages': 'Web_Pages',
        'Social Media': 'Social_Media',
        'Community': 'Community',
    }
    for cat_idx, (category, range_name) in enumerate(cat_range_names.items()):
        col_letter = get_column_letter(2 + cat_idx)
        types = content_types_by_cat[category]
        wb.defined_names.add(DefinedName(
            name=range_name,
            attr_text=f"'_Lookup'!${col_letter}$2:${col_letter}${1 + len(types)}"
        ))

    wb.defined_names.add(DefinedName(name="Countries", attr_text=f"'_Lookup'!$G$2:$G${1 + len(countries)}"))
    wb.defined_names.add(DefinedName(name="Languages", attr_text=f"'_Lookup'!$H$2:$H${1 + len(languages)}"))
    wb.defined_names.add(DefinedName(name="Audiences", attr_text=f"'_Lookup'!$I$2:$I${1 + len(audiences)}"))
    wb.defined_names.add(DefinedName(name="Priorities", attr_text=f"'_Lookup'!$K$2:$K${1 + len(priorities)}"))

    # ── Data Validations ──────────────────────────────────────────────
    max_rows = 502  # header + 500 data rows + 1

    dv_category = DataValidation(type="list", formula1="ContentCategories", allow_blank=False,
        showErrorMessage=True, errorTitle="Invalid", error="Select: Articles, Web Pages, Social Media, Community",
        showInputMessage=True, promptTitle="Content Category", prompt="Select a content category")
    dv_category.add(f"A2:A{max_rows}")
    ws.add_data_validation(dv_category)

    dv_type = DataValidation(type="list", formula1='=INDIRECT(SUBSTITUTE(A2," ","_"))', allow_blank=False,
        showErrorMessage=True, errorTitle="Invalid", error="Select Content Category first, then pick Content Type",
        showInputMessage=True, promptTitle="Content Type", prompt="Select Content Category first")
    dv_type.add(f"B2:B{max_rows}")
    ws.add_data_validation(dv_type)

    dv_country = DataValidation(type="list", formula1="Countries", allow_blank=False,
        showErrorMessage=True, errorTitle="Invalid", error="Select a valid country")
    dv_country.add(f"E2:E{max_rows}")
    ws.add_data_validation(dv_country)

    dv_language = DataValidation(type="list", formula1="Languages", allow_blank=False,
        showErrorMessage=True, errorTitle="Invalid", error="Select a valid language")
    dv_language.add(f"F2:F{max_rows}")
    ws.add_data_validation(dv_language)

    dv_audience = DataValidation(type="list", formula1="Audiences", allow_blank=False,
        showErrorMessage=True, errorTitle="Invalid", error="Select: General, Beginners, Professionals, Experts")
    dv_audience.add(f"G2:G{max_rows}")
    ws.add_data_validation(dv_audience)

    wc_str = ",".join(word_counts)
    dv_wordcount = DataValidation(type="list", formula1=f'"{wc_str}"', allow_blank=False,
        showErrorMessage=True, errorTitle="Invalid", error=f"Valid word counts: {wc_str}")
    dv_wordcount.add(f"H2:H{max_rows}")
    ws.add_data_validation(dv_wordcount)

    dv_priority = DataValidation(type="list", formula1="Priorities", allow_blank=False,
        showErrorMessage=True, errorTitle="Invalid", error="Select: High, Medium, Low")
    dv_priority.add(f"P2:P{max_rows}")
    ws.add_data_validation(dv_priority)

    # ── Cell comments on Title & Keywords headers ───────────────────
    from openpyxl.comments import Comment

    title_comment = Comment(
        "This field changes based on Content Category:\n"
        "• Articles → Article Title\n"
        "• Web Pages → Page Title\n"
        "• Social Media → Post Topic / Hook\n"
        "• Community → Post / Answer Title",
        "PromptMaxx"
    )
    title_comment.width = 280
    title_comment.height = 120
    ws.cell(row=1, column=3).comment = title_comment

    keywords_comment = Comment(
        "This field changes based on Content Category:\n"
        "• Articles → Target Keywords\n"
        "• Web Pages → Target Keywords\n"
        "• Social Media → Hashtags / Keywords\n"
        "• Community → Topics / Tags\n\n"
        "Enter as comma-separated values.",
        "PromptMaxx"
    )
    keywords_comment.width = 280
    keywords_comment.height = 140
    ws.cell(row=1, column=4).comment = keywords_comment

    # ── Pre-fill row 2 with domain defaults (if domain_id provided) ──
    domain_id = request.query_params.get('domain_id')
    if domain_id:
        try:
            domain = Domain.objects.get(id=domain_id)

            # E: Target Country — match domain.country to dropdown values
            domain_country = domain.country or ''
            matched_country = ''
            for display_name in countries:
                if display_name.lower() == domain_country.lower():
                    matched_country = display_name
                    break
            if not matched_country and countries:
                matched_country = countries[0]  # fallback to first
            if matched_country:
                ws.cell(row=2, column=5, value=matched_country)

            # F: Target Language — first value as default
            if languages:
                ws.cell(row=2, column=6, value=languages[0])

            # G: Target Audience — first value as default
            if audiences:
                ws.cell(row=2, column=7, value=audiences[0])

            # H: Word Count — default 1500
            ws.cell(row=2, column=8, value=1500)

            # I: Tone of Voice — from domain content guidelines
            if domain.tone_of_voice:
                ws.cell(row=2, column=9, value=domain.tone_of_voice)

            # J: Content Style — from domain content guidelines
            if domain.content_style:
                ws.cell(row=2, column=10, value=domain.content_style)

            # K: Key Messages — from domain content guidelines
            if domain.key_messages:
                ws.cell(row=2, column=11, value=domain.key_messages)

            # L: Topics to Avoid — from domain content guidelines
            if domain.topics_to_avoid:
                ws.cell(row=2, column=12, value=domain.topics_to_avoid)

            # P: Priority — default Medium
            ws.cell(row=2, column=16, value='Medium')

        except Domain.DoesNotExist:
            pass  # domain not found, skip pre-fill

    # ── Instructions sheet ─────────────────────────────────────────
    ws_instr = wb.create_sheet("Instructions", 0)
    wb.active = wb["Bulk Upload"]

    instr_title_font = Font(name="Calibri", bold=True, size=14, color="2563EB")
    instr_heading_font = Font(name="Calibri", bold=True, size=11)
    instr_body_font = Font(name="Calibri", size=10)
    instr_example_font = Font(name="Calibri", size=10, italic=True, color="666666")

    ws_instr.column_dimensions['A'].width = 5
    ws_instr.column_dimensions['B'].width = 30
    ws_instr.column_dimensions['C'].width = 60

    row = 2
    ws_instr.cell(row=row, column=2, value="Bulk Content Upload — Instructions").font = instr_title_font
    row += 2

    ws_instr.cell(row=row, column=2, value="Column Guide").font = instr_heading_font
    row += 1

    column_guide = [
        ("Content Category", "Select from: Articles, Web Pages, Social Media, Community"),
        ("Content Type", "Auto-filtered based on Category (e.g., Blog Post, Landing Page)"),
        ("Title / Page Title / Topic", "See category-specific names below"),
        ("Keywords / Hashtags / Tags", "See category-specific names below"),
        ("Target Country", "Market to target (e.g., United States)"),
        ("Target Language", "Language for the content (e.g., US English)"),
        ("Target Audience", "General, Beginners, Professionals, or Experts"),
        ("Word Count", "Target word count (50–3500)"),
        ("Tone of Voice", "e.g., Professional, Conversational, Friendly"),
        ("Content Style", "e.g., Informative, Persuasive, Engaging"),
        ("Key Messages", "Core messages to include (optional)"),
        ("Topics to Avoid", "Topics to exclude (optional)"),
        ("Additional Instructions", "Extra guidance for AI (optional)"),
        ("Reference URLs", "URLs for reference material (optional)"),
        ("Reference Descriptions", "Descriptions of references (optional)"),
        ("Priority", "High, Medium, or Low"),
    ]

    for col_name, desc in column_guide:
        ws_instr.cell(row=row, column=2, value=col_name).font = Font(name="Calibri", bold=True, size=10)
        ws_instr.cell(row=row, column=3, value=desc).font = instr_body_font
        row += 1

    row += 1
    ws_instr.cell(row=row, column=2, value="Title & Keywords — Per Category").font = instr_heading_font
    row += 1

    category_labels = [
        ("Category", "Title Column Means", "Keywords Column Means"),
        ("Articles", "Article Title", "Target Keywords (comma-separated)"),
        ("Web Pages", "Page Title", "Target Keywords (comma-separated)"),
        ("Social Media", "Post Topic / Hook", "Hashtags / Keywords (comma-separated)"),
        ("Community", "Post / Answer Title", "Topics / Tags (comma-separated)"),
    ]

    for i, (cat, title_label, kw_label) in enumerate(category_labels):
        font = Font(name="Calibri", bold=True, size=10) if i == 0 else instr_body_font
        ws_instr.cell(row=row, column=2, value=cat).font = font
        ws_instr.cell(row=row, column=3, value=f"{title_label}  |  {kw_label}").font = font if i == 0 else instr_example_font
        row += 1

    row += 1
    ws_instr.cell(row=row, column=2, value="Examples").font = instr_heading_font
    row += 1

    examples = [
        ("Articles → Blog Post", 'Title: "10 Best SEO Strategies"  |  Keywords: "seo strategies, seo tips"'),
        ("Web Pages → Landing Page", 'Title: "Transform Your Business"  |  Keywords: "business solutions, software"'),
        ("Social Media → Twitter/X Post", 'Title: "5 tips for founders"  |  Keywords: "#startups, #growthhacking"'),
        ("Community → Reddit Post", 'Title: "How to optimize React"  |  Keywords: "react, performance, optimization"'),
    ]

    for label, example in examples:
        ws_instr.cell(row=row, column=2, value=label).font = Font(name="Calibri", bold=True, size=10)
        ws_instr.cell(row=row, column=3, value=example).font = instr_example_font
        row += 1

    # ── Save & return ─────────────────────────────────────────────────
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="bulk_content_upload_template.xlsx"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def bulk_upload_content(request):
    """
    Upload .xlsx file for bulk content generation.
    Parses, validates, creates batch + items, and immediately starts queue engine.

    Form data:
    - file: The .xlsx file
    - domain_id: int
    """
    import openpyxl

    try:
        # Validate domain_id
        domain_id = request.data.get('domain_id') or request.POST.get('domain_id')
        if not domain_id:
            return Response({
                'status': 'error',
                'message': 'domain_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            domain = Domain.objects.get(
                id=int(domain_id),
                organisation=request.user.organisation
            )
        except Domain.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Domain not found or you do not have access'
            }, status=status.HTTP_404_NOT_FOUND)

        # Validate file
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({
                'status': 'error',
                'message': 'No file uploaded'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not uploaded_file.name.endswith('.xlsx'):
            return Response({
                'status': 'error',
                'message': 'Only .xlsx files are supported'
            }, status=status.HTTP_400_BAD_REQUEST)

        if uploaded_file.size > 5 * 1024 * 1024:  # 5MB
            return Response({
                'status': 'error',
                'message': 'File size must be under 5MB'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse Excel file
        try:
            wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
            ws = wb.active
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to parse Excel file: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse rows
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        wb.close()

        if not rows:
            return Response({
                'status': 'error',
                'message': 'Excel file has no data rows'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate and build items
        items_data = []
        errors = []

        for row_idx, row in enumerate(rows, start=2):
            # Skip completely empty rows
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue

            # Pad row to expected length
            row = list(row) + [None] * (16 - len(row)) if len(row) < 16 else list(row)

            content_category = str(row[0] or '').strip()
            content_type_name = str(row[1] or '').strip()
            title = str(row[2] or '').strip()
            keywords = str(row[3] or '').strip()
            target_country = str(row[4] or '').strip()
            target_language = str(row[5] or '').strip()
            target_audience = str(row[6] or '').strip()
            word_count_raw = row[7]
            tone = str(row[8] or '').strip()
            style = str(row[9] or '').strip()
            key_messages = str(row[10] or '').strip()
            topics_to_avoid = str(row[11] or '').strip()
            additional_instructions = str(row[12] or '').strip()
            reference_urls = str(row[13] or '').strip()
            reference_descriptions = str(row[14] or '').strip()
            priority_name = str(row[15] or '').strip()

            row_errors = []

            # Required fields
            if not title:
                row_errors.append('Title / Page Title / Topic is required')
            if not keywords:
                row_errors.append('Keywords are required')
            if not content_category:
                row_errors.append('Content Category is required')
            if not content_type_name:
                row_errors.append('Content Type is required')

            # Map content type
            article_type = BULK_CONTENT_TYPE_MAP.get((content_category, content_type_name))
            if not article_type and content_category and content_type_name:
                row_errors.append(
                    f'Invalid Content Category/Type combination: "{content_category}" / "{content_type_name}"'
                )

            # Map country
            country_code = BULK_COUNTRY_MAP.get(target_country, 'united_states')

            # Map language
            language_code = BULK_LANGUAGE_MAP.get(target_language, 'us_english')

            # Map audience
            audience_code = BULK_AUDIENCE_MAP.get(target_audience, 'general')

            # Map priority
            priority_code = BULK_PRIORITY_MAP.get(priority_name, 'medium')

            # Parse word count
            try:
                word_count = int(word_count_raw) if word_count_raw else 1500
            except (ValueError, TypeError):
                word_count = 1500
                row_errors.append(f'Invalid word count: {word_count_raw}')

            if row_errors:
                errors.append({'row': row_idx, 'errors': row_errors})
            else:
                items_data.append({
                    'row_number': row_idx,
                    'content_category': content_category,
                    'content_type': content_type_name,
                    'title': title,
                    'keywords': keywords,
                    'article_type': article_type,
                    'target_country': country_code,
                    'target_language': language_code,
                    'target_audience': audience_code,
                    'word_count': word_count,
                    'tone': tone or 'professional',
                    'style': style or 'informative',
                    'key_messages': key_messages,
                    'topics_to_avoid': topics_to_avoid,
                    'additional_instructions': additional_instructions,
                    'reference_urls': reference_urls,
                    'reference_descriptions': reference_descriptions,
                    'priority': priority_code,
                })

        if errors:
            return Response({
                'status': 'error',
                'message': f'Validation failed for {len(errors)} row(s)',
                'validation_errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        if not items_data:
            return Response({
                'status': 'error',
                'message': 'No valid data rows found'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Clean up previous completed batches for this domain
        # (items are deleted automatically via CASCADE)
        BulkUploadBatch.objects.filter(
            domain=domain,
            status__in=['completed', 'completed_with_errors', 'failed'],
        ).delete()

        # Create batch and items
        with transaction.atomic():
            batch = BulkUploadBatch.objects.create(
                domain=domain,
                uploaded_by=request.user,
                file_name=uploaded_file.name,
                status='processing',
                total_items=len(items_data),
            )

            bulk_items = []
            for item_data in items_data:
                bulk_items.append(BulkUploadItem(
                    batch=batch,
                    **item_data,
                    status='processed',
                ))
            BulkUploadItem.objects.bulk_create(bulk_items)

        # Start queue engine immediately
        thread = threading.Thread(
            target=_run_bulk_generation_queue,
            args=(batch.id,),
            daemon=True
        )
        thread.start()

        logger.info(
            f"Bulk upload batch {batch.id} created with {len(items_data)} items, "
            f"queue engine started"
        )

        # Return batch detail
        serializer = BulkUploadBatchSerializer(batch)
        return Response({
            'status': 'success',
            'message': f'Uploaded {len(items_data)} items. Generation started automatically.',
            'data': serializer.data
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Bulk upload error: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Bulk upload failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bulk_upload_batches(request):
    """
    List all bulk upload batches for the user's organisation.
    Query params: domain_id (optional)
    """
    try:
        batches = BulkUploadBatch.objects.filter(
            domain__organisation=request.user.organisation
        )

        domain_id = request.query_params.get('domain_id')
        if domain_id:
            batches = batches.filter(domain_id=domain_id)

        serializer = BulkUploadBatchListSerializer(batches, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    except Exception as e:
        logger.error(f"Error fetching bulk upload batches: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bulk_upload_batch_detail(request, batch_id):
    """
    Get batch detail with all items and their statuses.
    Used for polling by the frontend.
    """
    try:
        batch = get_object_or_404(
            BulkUploadBatch,
            id=batch_id,
            domain__organisation=request.user.organisation
        )

        serializer = BulkUploadBatchSerializer(batch)
        return Response({
            'status': 'success',
            'data': serializer.data
        })

    except Exception as e:
        logger.error(f"Error fetching batch detail: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retry_bulk_upload_item(request, item_id):
    """
    Retry a failed item. Resets status to 'processed' and spawns a
    single-item background generation thread.
    """
    try:
        item = get_object_or_404(
            BulkUploadItem,
            id=item_id,
            batch__domain__organisation=request.user.organisation
        )

        if item.status != 'generation_failed':
            return Response({
                'status': 'error',
                'message': f'Can only retry items with status "generation_failed", current: "{item.status}"'
            }, status=status.HTTP_400_BAD_REQUEST)

        item.status = 'processed'
        item.error_message = None
        item.retry_count += 1
        item.save(update_fields=['status', 'error_message', 'retry_count', 'modified_at'])

        # Spawn single-item generation thread
        thread = threading.Thread(
            target=_run_single_item_generation,
            args=(item.id,),
            daemon=True
        )
        thread.start()

        serializer = BulkUploadItemSerializer(item)
        return Response({
            'status': 'success',
            'message': 'Retry started',
            'data': serializer.data
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Error retrying bulk item: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_bulk_upload_item_status(request, item_id):
    """
    Manually advance an item through the review workflow.
    Body: { "status": "in_review" | "reviewed" | "approved" }
    """
    try:
        item = get_object_or_404(
            BulkUploadItem,
            id=item_id,
            batch__domain__organisation=request.user.organisation
        )

        new_status = request.data.get('status')
        if not new_status:
            return Response({
                'status': 'error',
                'message': 'status field is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        valid_next = BULK_VALID_STATUS_TRANSITIONS.get(item.status, [])
        if new_status not in valid_next:
            return Response({
                'status': 'error',
                'message': (
                    f'Invalid status transition: "{item.status}" → "{new_status}". '
                    f'Valid transitions from "{item.status}": {valid_next or "none"}'
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        item.status = new_status
        item.save(update_fields=['status', 'modified_at'])

        # Sync review status to the real GeneratedContent via ContentComment
        if item.generated_content:
            content = item.generated_content

            if new_status == 'in_review':
                # Create a pending review comment to trigger "In Review" in Content Planner
                existing = ContentComment.objects.filter(
                    content=content,
                    author=request.user,
                    comment='Bulk upload review — pending review',
                    status='pending',
                ).first()
                if not existing:
                    ContentComment.objects.create(
                        content=content,
                        author=request.user,
                        selected_text=content.title,
                        comment='Bulk upload review — pending review',
                        status='pending',
                    )

            elif new_status == 'approved':
                # Resolve all pending comments to trigger "Reviewed" in Content Planner
                ContentComment.objects.filter(
                    content=content,
                    status='pending',
                ).update(
                    status='accepted',
                    resolved_by=request.user,
                    resolved_at=timezone.now(),
                )

        serializer = BulkUploadItemSerializer(item)
        return Response({
            'status': 'success',
            'message': f'Status updated to {new_status}',
            'data': serializer.data
        })

    except Exception as e:
        logger.error(f"Error updating bulk item status: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================
# Issue 8A: URL Reading endpoint
# =============================================
def _fetch_youtube_metadata(url):
    """Fetch YouTube video metadata using oEmbed API (no API key needed)."""
    import re as _re
    # Extract video ID from various YouTube URL formats
    patterns = [
        r'(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})',
    ]
    video_id = None
    for pattern in patterns:
        match = _re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break

    if not video_id:
        return None

    try:
        oembed_url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
        resp = requests.get(oembed_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        title = data.get('title', '')
        author = data.get('author_name', '')
        description = f"Video by {author}" if author else ''
        thumbnail = data.get('thumbnail_url', '')
        text_content = f"Title: {title}\nAuthor: {author}\nThumbnail: {thumbnail}"
        return {
            'title': title,
            'description': description,
            'text_content': text_content,
            'word_count': len(text_content.split()),
            'url': url,
            'thumbnail': thumbnail,
        }
    except Exception as e:
        logger.warning(f"YouTube oEmbed failed for {url}: {e}")
        return None


def _fetch_vimeo_metadata(url):
    """Fetch Vimeo video metadata using oEmbed API."""
    try:
        oembed_url = f'https://vimeo.com/api/oembed.json?url={url}'
        resp = requests.get(oembed_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        title = data.get('title', '')
        author = data.get('author_name', '')
        description = data.get('description', '') or f"Video by {author}"
        thumbnail = data.get('thumbnail_url', '')
        text_content = f"Title: {title}\nAuthor: {author}\nDescription: {description}"
        return {
            'title': title,
            'description': description,
            'text_content': text_content,
            'word_count': len(text_content.split()),
            'url': url,
            'thumbnail': thumbnail,
        }
    except Exception as e:
        logger.warning(f"Vimeo oEmbed failed for {url}: {e}")
        return None


def _fetch_image_metadata(url):
    """Fetch basic metadata for image URLs."""
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        content_type = resp.headers.get('Content-Type', '')
        content_length = resp.headers.get('Content-Length', '')
        # Extract filename from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        filename = parsed.path.split('/')[-1] if parsed.path else url
        size_kb = f"{int(content_length) // 1024}KB" if content_length else 'unknown size'
        return {
            'title': filename,
            'description': f"Image ({content_type.split(';')[0]}, {size_kb})",
            'text_content': f"Image: {filename}\nType: {content_type}\nSize: {size_kb}\nURL: {url}",
            'word_count': 0,
            'url': url,
        }
    except Exception as e:
        logger.warning(f"Image metadata fetch failed for {url}: {e}")
        return None


def _fetch_url_content(url, max_words=3500, timeout=15):
    """
    Fetch and extract readable text content from a URL for use in content generation.
    Returns dict with 'title', 'text_content', 'word_count', 'url' or None on failure.
    """
    try:
        if not url or not url.strip():
            return None

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        url_lower = url.lower()
        # Skip non-text URLs
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico')
        if any(url_lower.split('?')[0].endswith(ext) for ext in image_extensions):
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; PromptmaxxBot/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get('Content-Type', '')
        if content_type.startswith('image/'):
            return None

        html_content = resp.text

        # Try trafilatura for clean text extraction
        try:
            import trafilatura
            extracted = trafilatura.extract(html_content, include_comments=False, include_tables=True)
            if extracted and len(extracted.strip()) > 50:
                words = extracted.split()
                if len(words) > max_words:
                    extracted = ' '.join(words[:max_words]) + '\n[Content truncated]'
                metadata = trafilatura.extract_metadata(html_content)
                title = metadata.title if metadata and metadata.title else ''
                return {
                    'title': title,
                    'text_content': extracted,
                    'word_count': len(extracted.split()),
                    'url': url,
                }
        except ImportError:
            pass

        # Fallback: basic BeautifulSoup extraction
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe', 'noscript']):
                tag.decompose()
            main_content = (
                soup.find('article') or soup.find('main') or
                soup.find('div', {'role': 'main'}) or soup.body or soup
            )
            text = main_content.get_text(separator='\n', strip=True)
            words = text.split()
            if len(words) > max_words:
                text = ' '.join(words[:max_words]) + '\n[Content truncated]'
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else ''
            return {
                'title': title,
                'text_content': text,
                'word_count': len(text.split()),
                'url': url,
            }
        except ImportError:
            pass

        return None
    except Exception as e:
        logger.warning(f"Failed to fetch URL content for {url}: {e}")
        return None


def _enrich_references_with_content(references, max_refs=5, cache=None):
    """
    Fetch actual content for reference URLs to prevent AI hallucination.
    Adds 'fetched_content' and 'fetched_title' keys to each reference dict.

    Pass ``cache`` (a dict) to reuse fetched content across multiple calls —
    the bulk generation queue passes a single cache so the same URL appearing
    in many rows is only fetched once per batch.
    """
    enriched = []
    for ref in references[:max_refs]:
        url = ref.get('url', '')
        if not url:
            enriched.append(ref)
            continue

        # Normalize URL for cache key so trailing spaces / case don't miss.
        cache_key = url.strip().lower()
        if cache is not None and cache_key in cache:
            fetched = cache[cache_key]
        else:
            fetched = _fetch_url_content(url, max_words=3500, timeout=15)
            if cache is not None:
                cache[cache_key] = fetched

        ref_copy = dict(ref)
        if fetched and fetched.get('text_content'):
            ref_copy['fetched_content'] = fetched['text_content']
            ref_copy['fetched_title'] = fetched.get('title', '')
            logger.info(f"[REF-URL] Using {fetched['word_count']} words from {url}")
        else:
            ref_copy['fetched_content'] = None
            logger.warning(f"[REF-URL] Could not fetch content from {url}")
        enriched.append(ref_copy)

    return enriched


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def read_url(request):
    """
    Fetch and extract readable text content from a URL.
    Used in the wizard References step to auto-populate reference descriptions.
    Supports: YouTube, Vimeo, image URLs, and general web pages.

    Expected request body:
    {
        "url": str
    }
    """
    try:
        url = request.data.get('url', '').strip()
        if not url:
            return Response({
                'status': 'error',
                'message': 'URL is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        url_lower = url.lower()

        # YouTube URLs - use oEmbed API
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            result = _fetch_youtube_metadata(url)
            if result:
                return Response({'status': 'success', 'data': result})

        # Vimeo URLs - use oEmbed API
        if 'vimeo.com' in url_lower:
            result = _fetch_vimeo_metadata(url)
            if result:
                return Response({'status': 'success', 'data': result})

        # Image URLs - fetch HEAD metadata
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico')
        if any(url_lower.split('?')[0].endswith(ext) for ext in image_extensions):
            result = _fetch_image_metadata(url)
            if result:
                return Response({'status': 'success', 'data': result})

        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; PromptmaxxBot/1.0)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        try:
            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            return Response({
                'status': 'error',
                'message': f'Failed to fetch URL: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if response is actually an image (content-type check)
        content_type = resp.headers.get('Content-Type', '')
        if content_type.startswith('image/'):
            result = _fetch_image_metadata(url)
            if result:
                return Response({'status': 'success', 'data': result})

        html_content = resp.text

        # Try trafilatura for clean text extraction
        try:
            import trafilatura
            extracted = trafilatura.extract(html_content, include_comments=False, include_tables=True)
            if extracted and len(extracted.strip()) > 50:
                # Also extract metadata
                metadata = trafilatura.extract_metadata(html_content)
                title = metadata.title if metadata and metadata.title else ''
                description = metadata.description if metadata and metadata.description else ''
                return Response({
                    'status': 'success',
                    'data': {
                        'title': title,
                        'description': description,
                        'text_content': extracted[:10000],  # Cap at 10k chars
                        'word_count': len(extracted.split()),
                        'url': url
                    }
                })
        except ImportError:
            logger.warning("trafilatura not installed, falling back to basic extraction")

        # Fallback: basic HTML parsing with BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            title = ''
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)

            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')

            # Remove noise elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header',
                                 'aside', 'form', 'iframe', 'noscript']):
                element.decompose()

            # Try to find main content container first
            main_content = (
                soup.find('article') or
                soup.find('main') or
                soup.find('div', {'role': 'main'}) or
                soup.find('div', class_=lambda c: c and any(
                    x in str(c).lower() for x in ['content', 'article', 'post-body', 'entry-content']
                ))
            )

            content_source = main_content if main_content else soup.body or soup

            # Extract text and deduplicate repeated lines
            text = content_source.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]

            # Remove duplicate consecutive lines and near-duplicate repeated blocks
            seen = set()
            unique_lines = []
            for line in lines:
                # Skip very short lines that are likely navigation/button text
                if len(line) < 10:
                    continue
                # Deduplicate by normalized text
                normalized = line.lower().strip()[:100]
                if normalized not in seen:
                    seen.add(normalized)
                    unique_lines.append(line)

            text_content = '\n'.join(unique_lines)

            return Response({
                'status': 'success',
                'data': {
                    'title': title,
                    'description': description,
                    'text_content': text_content[:10000],
                    'word_count': len(text_content.split()),
                    'url': url
                }
            })
        except ImportError:
            # Last resort: regex-based extraction
            import re
            clean = re.sub(r'<[^>]+>', ' ', html_content)
            clean = re.sub(r'\s+', ' ', clean).strip()
            return Response({
                'status': 'success',
                'data': {
                    'title': '',
                    'description': '',
                    'text_content': clean[:10000],
                    'word_count': len(clean.split()),
                    'url': url
                }
            })

    except Exception as e:
        logger.error(f"Error reading URL: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error reading URL: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================
# Issue 8B: Keyword Suggestions endpoint
# =============================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_keywords(request):
    """
    AI-powered keyword suggestions based on title and article type.

    Expected request body:
    {
        "title": str,
        "article_type": str (optional),
        "domain_url": str (optional),
        "existing_keywords": str (optional)
    }
    """
    try:
        title = request.data.get('title', '').strip()
        if not title:
            return Response({
                'status': 'error',
                'message': 'Title is required for keyword suggestions'
            }, status=status.HTTP_400_BAD_REQUEST)

        article_type = request.data.get('article_type', 'blog')
        domain_url = request.data.get('domain_url', '')
        existing_keywords = request.data.get('existing_keywords', '')

        generator = ClaudeContentGenerator()

        system_prompt = """You are an expert SEO keyword researcher. Suggest highly relevant keywords for content optimization.
Return a JSON array of keyword objects. Each object must have:
- "keyword": the keyword phrase
- "intent": one of "informational", "transactional", "navigational", "commercial"
- "relevance": "high", "medium", or "low"

Return ONLY valid JSON array, no markdown, no explanation."""

        user_prompt = f"""Suggest 12-15 SEO keywords for the following content:

Title: {title}
Content Type: {article_type}
"""
        if domain_url:
            user_prompt += f"Website: {domain_url}\n"
        if existing_keywords:
            user_prompt += f"Already selected keywords (suggest different ones): {existing_keywords}\n"

        user_prompt += """
Focus on:
- Primary keywords (high search volume, directly relevant)
- Long-tail keywords (specific phrases with clear intent)
- Related/semantic keywords
- Question-based keywords (what, how, why)

Return ONLY a JSON array."""

        try:
            response = generator.client.messages.create(
                model=generator.model,
                max_tokens=1000,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            import json
            response_text = response.content[0].text.strip()
            # Handle potential markdown wrapping
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            keywords = json.loads(response_text)

            return Response({
                'status': 'success',
                'data': {
                    'suggestions': keywords
                }
            })

        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract keywords as plain text
            raw_text = response.content[0].text.strip()
            simple_keywords = [
                {'keyword': line.strip().strip('-•*').strip(), 'intent': 'informational', 'relevance': 'medium'}
                for line in raw_text.split('\n')
                if line.strip() and not line.strip().startswith(('[', '{', ']', '}'))
            ][:15]
            return Response({
                'status': 'success',
                'data': {
                    'suggestions': simple_keywords
                }
            })

    except Exception as e:
        logger.error(f"Error suggesting keywords: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error suggesting keywords: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================
# Issue 8C: Reschedule / Plan content endpoint
# =============================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def plan_content(request):
    """
    Create a planned content entry (title + keywords + type only, no generation).
    Used from the calendar to plan future blog posts.

    Expected request body:
    {
        "domain_id": int,
        "title": str,
        "keywords": str,
        "article_type": str,
        "scheduled_date": str (ISO datetime),
        "priority": str (optional)
    }
    """
    try:
        domain_id = request.data.get('domain_id')
        title = request.data.get('title', '').strip()
        keywords = request.data.get('keywords', '').strip()

        if not domain_id or not title:
            return Response({
                'status': 'error',
                'message': 'domain_id and title are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            domain = Domain.objects.get(
                id=domain_id,
                organisation=request.user.organisation
            )
        except Domain.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Domain not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)

        scheduled_date = request.data.get('scheduled_date')
        if scheduled_date:
            from django.utils.dateparse import parse_datetime
            scheduled_date = parse_datetime(scheduled_date)

        content = GeneratedContent.objects.create(
            domain=domain,
            title=title,
            content_html='',
            keywords=keywords or '',
            article_type=request.data.get('article_type', 'blog'),
            status='planned',
            priority=request.data.get('priority', 'medium'),
            scheduled_date=scheduled_date,
            source_type='manual',
            tone=request.data.get('tone', 'professional'),
            style=request.data.get('style', 'informative'),
            goal=request.data.get('goal', 'educate'),
            audience=request.data.get('audience', 'general'),
            depth=request.data.get('depth', 'comprehensive'),
            word_count=request.data.get('word_count', 1500),
        )

        serializer = GeneratedContentSerializer(content)
        return Response({
            'status': 'success',
            'message': 'Content planned successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error planning content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def reschedule_content(request, content_id):
    """
    Reschedule content to a new date.

    Expected request body:
    {
        "scheduled_date": str (ISO datetime)
    }
    """
    try:
        content = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )

        scheduled_date = request.data.get('scheduled_date')
        if scheduled_date:
            from django.utils.dateparse import parse_datetime
            content.scheduled_date = parse_datetime(scheduled_date)
        else:
            content.scheduled_date = None

        content.save(update_fields=['scheduled_date', 'modified_at'])

        serializer = GeneratedContentSerializer(content)
        return Response({
            'status': 'success',
            'message': 'Content rescheduled successfully',
            'data': serializer.data
        })

    except Exception as e:
        logger.error(f"Error rescheduling content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================
# Issue 8D: Refurbish content endpoint
# =============================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refurbish_content(request):
    """
    Refurbish/repurpose existing content.

    Expected request body:
    {
        "content_id": int,
        "refurbish_type": str ("refresh_stats", "improve_seo", "expand", "repurpose"),
        "new_article_type": str (required if refurbish_type is "repurpose"),
        "new_keywords": str (optional, for improve_seo),
        "additional_instructions": str (optional)
    }
    """
    try:
        content_id = request.data.get('content_id')
        refurbish_type = request.data.get('refurbish_type', 'refresh_stats')

        if not content_id:
            return Response({
                'status': 'error',
                'message': 'content_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        original = get_object_or_404(
            GeneratedContent,
            id=content_id,
            domain__organisation=request.user.organisation
        )

        if not original.content_html or len(original.content_html.strip()) < 50:
            return Response({
                'status': 'error',
                'message': 'Original content is too short to refurbish'
            }, status=status.HTTP_400_BAD_REQUEST)

        generator = ClaudeContentGenerator()

        refurbish_instructions = {
            'refresh_stats': """Refresh this content by:
- Updating any outdated statistics, facts, or references
- Ensuring all claims are current and accurate
- Improving any sections that could be more detailed
- Keeping the same structure and tone
- Return the complete updated HTML content""",

            'improve_seo': f"""Optimize this content for better SEO by:
- Improving keyword placement and density for: {request.data.get('new_keywords', original.keywords)}
- Enhancing headings for better search visibility
- Adding relevant internal linking opportunities (as placeholder text)
- Improving meta-relevant content in introduction and conclusion
- Ensuring proper use of H2/H3 heading hierarchy
- Return the complete optimized HTML content""",

            'expand': """Expand this content by:
- Adding more depth to existing sections
- Including additional examples and case studies
- Adding new relevant subsections where appropriate
- Expanding the introduction and conclusion
- Target approximately 50% more content than the original
- Return the complete expanded HTML content""",

            'repurpose': f"""Repurpose this content as a {request.data.get('new_article_type', 'listicle')} by:
- Restructuring the content for the new format
- Adapting the tone and style appropriately
- Maintaining the core information and insights
- Adding format-specific elements (e.g., numbered items for listicle, step-by-step for guide)
- Return the complete repurposed HTML content""",
        }

        instructions = refurbish_instructions.get(refurbish_type, refurbish_instructions['refresh_stats'])
        additional = request.data.get('additional_instructions', '')
        if additional:
            instructions += f"\n\nAdditional instructions: {additional}"

        system_prompt = """You are an expert content editor and SEO specialist. Refurbish the provided content according to the instructions.
- Maintain proper HTML formatting with semantic tags (h2, h3, p, ul, ol, strong, em)
- Keep the content factually accurate and up-to-date
- Ensure SEO optimization
- Return ONLY the HTML content (no markdown, no code blocks)"""

        user_prompt = f"""Original content title: {original.title}
Original keywords: {original.keywords}

Original HTML content:
{original.content_html}

Instructions:
{instructions}

Return ONLY the refurbished HTML content."""

        max_tokens = ClaudeContentGenerator._calculate_max_tokens(
            int(original.word_count * 1.5) if refurbish_type == 'expand' else original.word_count
        )

        import time
        start_time = time.time()

        response = generator.client.messages.create(
            model=generator.model,
            max_tokens=max_tokens,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        generation_time = time.time() - start_time
        refurbished_html = response.content[0].text.strip()

        # Clean up markdown artifacts
        refurbished_html = generator.post_process_content(refurbished_html)

        # Calculate actual word count
        import re
        text_only = re.sub(r'<[^>]+>', ' ', refurbished_html)
        actual_word_count = len(text_only.split())

        # Generate new meta tags
        meta_result = generator.generate_meta_tags(
            title=original.title,
            content_html=refurbished_html,
            keywords=request.data.get('new_keywords', original.keywords),
        )

        # Determine new article type
        new_article_type = original.article_type
        if refurbish_type == 'repurpose' and request.data.get('new_article_type'):
            new_article_type = request.data.get('new_article_type')

        # Create new content entry (preserves original)
        new_content = GeneratedContent.objects.create(
            domain=original.domain,
            title=original.title if refurbish_type != 'repurpose' else f"{original.title} ({new_article_type})",
            content_html=refurbished_html,
            meta_title=meta_result['meta_title'],
            meta_description=meta_result['meta_description'],
            source_type=original.source_type,
            source_id=original.source_id,
            source_reference=original.source_reference,
            article_type=new_article_type,
            keywords=request.data.get('new_keywords', original.keywords),
            tone=original.tone,
            style=original.style,
            goal=original.goal,
            audience=original.audience,
            depth=original.depth,
            word_count=original.word_count,
            actual_word_count=actual_word_count,
            status='generated',
            priority=original.priority,
            scheduled_date=original.scheduled_date,
            model_used=generator.model,
            generation_time_seconds=round(generation_time, 2),
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            refurbished_from=original,
        )

        serializer = GeneratedContentSerializer(new_content)
        return Response({
            'status': 'success',
            'message': f'Content refurbished successfully ({refurbish_type})',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error refurbishing content: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error refurbishing content: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================
# Issue 12: Extract text from uploaded file
# =============================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def extract_file_text(request):
    """
    Extract text content from an uploaded file (PDF, DOCX, PPTX, CSV, XLSX).
    Used in the wizard References step for file-based references.
    The file is NOT stored permanently — text is extracted and returned.

    Expected: multipart form with 'file' field
    """
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({
                'status': 'error',
                'message': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check file size (10MB max for reference extraction)
        if uploaded_file.size > 10 * 1024 * 1024:
            return Response({
                'status': 'error',
                'message': 'File size exceeds 10MB limit'
            }, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded_file.name.lower()
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''

        ext_to_type = {
            'pdf': 'pdf',
            'docx': 'docx',
            'doc': 'docx',
            'pptx': 'pptx',
            'ppt': 'pptx',
            'csv': 'csv',
            'xlsx': 'xlsx',
            'xls': 'xlsx',
            'txt': 'txt',
        }

        file_type = ext_to_type.get(ext)
        if not file_type:
            return Response({
                'status': 'error',
                'message': f'Unsupported file type: .{ext}. Supported: PDF, DOCX, PPTX, CSV, XLSX, TXT'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Reuse the extraction function from domains app
        from domains.views import _extract_text_from_file

        if file_type == 'txt':
            extracted_text = uploaded_file.read().decode('utf-8', errors='replace')
        else:
            extracted_text = _extract_text_from_file(uploaded_file, file_type)

        if not extracted_text or not extracted_text.strip():
            return Response({
                'status': 'error',
                'message': 'Could not extract text from the file. The file may be empty or contain only images.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Cap extracted text at 15k chars for reference use
        extracted_text = extracted_text[:15000]

        return Response({
            'status': 'success',
            'data': {
                'filename': uploaded_file.name,
                'extracted_text': extracted_text,
                'word_count': len(extracted_text.split()),
                'file_type': file_type
            }
        })

    except Exception as e:
        logger.error(f"Error extracting file text: {str(e)}", exc_info=True)
        return Response({
            'status': 'error',
            'message': f'Error extracting file text: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
