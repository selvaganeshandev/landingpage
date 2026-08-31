"""API endpoints for image generation in the content editor.

Two endpoints, matching the two stages:

    POST /content/image-prompt/     -> writes an image prompt from a passage
    POST /content/generate-image/   -> renders a (possibly edited) prompt

Both are scoped to the caller's organisation. Kept in their own module rather
than appended to views.py, which is already 4,400+ lines.
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain

from .image_generation import (
    STYLES,
    ImageGenerationError,
    append_brand_colors,
    generate_image_prompt,
    render_image,
    save_image,
)

logger = logging.getLogger(__name__)

MAX_SELECTED_TEXT = 5000
MAX_INSTRUCTIONS = 500


def _error(message, code):
    return Response({'status': 'error', 'message': message}, status=code)


def _resolve_domain(request, domain_id):
    """Return the domain if the caller's organisation owns it, else None."""
    if not domain_id:
        return None
    try:
        return Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except (Domain.DoesNotExist, ValueError, TypeError):
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def image_styles(request):
    """The six illustration styles, for populating the picker."""
    return Response({
        'status': 'success',
        'data': [
            {
                'value': value,
                'label': label,
                'description': description,
                'photographic': value in {'realistic', 'real-world'},
            }
            for value, (label, description) in STYLES.items()
        ],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def image_prompt(request):
    """Stage 1 — turn a selected passage into an image prompt."""
    data = request.data or {}

    selected_text = (data.get('selected_text') or '').strip()
    if not selected_text:
        return _error('Select some text in the article first.', status.HTTP_400_BAD_REQUEST)
    if len(selected_text) > MAX_SELECTED_TEXT:
        selected_text = selected_text[:MAX_SELECTED_TEXT]

    style = (data.get('style') or 'realistic').strip()
    if style not in STYLES:
        return _error(
            f'Unknown style "{style}". Expected one of: {", ".join(STYLES)}',
            status.HTTP_400_BAD_REQUEST,
        )

    instructions = (data.get('additional_instructions') or '').strip()[:MAX_INSTRUCTIONS]

    # Title and keyword are context only — a missing one degrades quality
    # slightly but should never block the request.
    article_title = (data.get('title') or '').strip() or 'Untitled article'
    keyword = (data.get('keyword') or '').strip()

    domain = _resolve_domain(request, data.get('domain_id'))
    if data.get('domain_id') and domain is None:
        return _error(
            'Domain not found or you do not have access to it.',
            status.HTTP_404_NOT_FOUND,
        )

    try:
        prompt = generate_image_prompt(
            article_title=article_title,
            selected_text=selected_text,
            style=style,
            keyword=keyword,
            additional_instructions=instructions,
            org=request.user.organisation,
            user=request.user,
        )
    except ImageGenerationError as exc:
        logger.warning('Image prompt generation failed: %s', exc)
        return _error(str(exc), exc.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.exception('Unexpected error generating image prompt')
        return _error(f'Unexpected error: {exc}', status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'status': 'success', 'data': {'prompt': prompt}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_image(request):
    """Stage 2 — render the (possibly user-edited) prompt to an image."""
    data = request.data or {}

    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return _error('Generate or write a prompt first.', status.HTTP_400_BAD_REQUEST)

    domain = _resolve_domain(request, data.get('domain_id'))
    if data.get('domain_id') and domain is None:
        return _error(
            'Domain not found or you do not have access to it.',
            status.HTTP_404_NOT_FOUND,
        )

    # Brand colors are applied a second time here so they survive the user
    # editing the prompt by hand between the two stages.
    colors = data.get('brand_colors') or []
    if isinstance(colors, list) and colors:
        prompt = append_brand_colors(prompt, [str(c) for c in colors][:5])

    try:
        mime, raw = render_image(prompt, org=request.user.organisation, user=request.user)
        url = save_image(raw, mime)
    except ImageGenerationError as exc:
        logger.warning('Image rendering failed: %s', exc)
        return _error(str(exc), exc.status_code)
    except OSError as exc:
        logger.exception('Could not write the generated image to disk')
        return _error(
            f'The image was generated but could not be saved: {exc}',
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception('Unexpected error generating image')
        return _error(f'Unexpected error: {exc}', status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'status': 'success',
        'data': {'url': url, 'mime_type': mime, 'bytes': len(raw)},
    })
