from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from decouple import config
import logging
import requests
import re

from .models import GeneratedContent, CMSProvider, ScheduledPublication, ContentComment
from .serializers import (
    GeneratedContentSerializer, ContentGenerationRequestSerializer,
    CMSProviderSerializer, CMSProviderCreateSerializer,
    ScheduledPublicationSerializer, PublishContentSerializer,
    ContentCommentSerializer, CreateContentCommentSerializer
)
from .claude_content_generator import ClaudeContentGenerator
from domains.models import Domain
from django.db import transaction
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
            'brand_values': validated_data.get('brand_values', ''),
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
        }

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
            'brand_values': validated_data.get('brand_values', ''),
        }

        # Generate content from outline
        logger.info(f"Generating content from outline for domain {domain.id}: {validated_data['title']}")
        generation_result = generator.generate_content_from_outline(generation_params, outline)

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
