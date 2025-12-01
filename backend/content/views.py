from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import Http404
import logging

from .models import GeneratedContent
from .serializers import GeneratedContentSerializer, ContentGenerationRequestSerializer
from .claude_content_generator import ClaudeContentGenerator
from domains.models import Domain

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

        # Prepare generation parameters
        generation_params = {
            'title': validated_data['title'],
            'keywords': validated_data['keywords'],
            'article_type': validated_data.get('article_type', 'blog'),
            'tone': validated_data.get('tone', 'professional'),
            'style': validated_data.get('style', 'informative'),
            'goal': validated_data.get('goal', 'educate'),
            'audience': validated_data.get('audience', 'general'),
            'depth': validated_data.get('depth', 'comprehensive'),
            'word_count': validated_data.get('word_count', 1500),
            'source_reference': validated_data.get('source_reference', '')
        }

        # Generate content using Claude
        logger.info(f"Generating content for domain {domain.id}: {validated_data['title']}")
        generation_result = generator.generate_content(generation_params)

        # Create GeneratedContent record
        generated_content = GeneratedContent.objects.create(
            domain=domain,
            title=validated_data['title'],
            content_html=generation_result['content_html'],
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

        # Order by created_at descending
        queryset = queryset.order_by('-created_at')

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

