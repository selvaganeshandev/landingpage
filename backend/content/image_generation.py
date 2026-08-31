"""Image generation for the content editor — two stages, both over OpenRouter.

Stage 1 turns a passage of the article into one vivid image prompt using a TEXT
model. Stage 2 renders that prompt to pixels using an IMAGE model. The user edits
the prompt in between, which is where most of the perceived quality comes from.

Both stages hit the same endpoint (``/chat/completions``) with the same
credential. Stage 2 is not a separate API — it is a chat completion that asks for
an image back via ``modalities``.

Why this does NOT reuse ``core.openrouter_client``: that module is a
Claude-shaped adapter whose ``_to_message`` keeps only ``message.content`` and
drops ``message.images`` entirely, so an image response would come back empty.
The render call below therefore talks to the endpoint directly.
"""

from __future__ import annotations

import base64
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Neither renderer streams and payloads run to megabytes, so a stalled
# connection would otherwise hold a request handler open forever.
RENDER_TIMEOUT = 180
PROMPT_TIMEOUT = 60

# Extension per mime type. Anything unexpected falls back to .png rather than
# writing a file the user's OS cannot open.
_MIME_EXT = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/webp': 'webp',
    'image/gif': 'gif',
}

# value -> (label, description sent to the model)
STYLES: Dict[str, Tuple[str, str]] = {
    'realistic': (
        'Realistic',
        'photorealistic rendering, natural lighting, fine detail, as if shot on '
        'a high-end camera',
    ),
    'real-world': (
        'Real world',
        'a genuine candid photograph of a real scene or setting, documentary '
        'style, unposed',
    ),
    'cartoon': (
        'Cartoonic',
        'flat cartoon illustration, bold clean outlines, vibrant simplified '
        'colors, playful and friendly',
    ),
    'animation': (
        '3D animation',
        'Pixar-style 3D animated render, soft global illumination, rounded '
        'stylized forms',
    ),
    'watercolor': (
        'Watercolor',
        'artistic watercolor illustration, visible brush texture, soft color '
        'bleeds, hand-drawn feel',
    ),
    'flat-design': (
        'Flat design',
        'modern flat vector illustration, minimal geometric shapes, limited '
        'restrained color palette',
    ),
}

PHOTOGRAPHIC = {'realistic', 'real-world'}


class ImageGenerationError(Exception):
    """Raised with a message intended to be shown to the user verbatim.

    Upstream messages from OpenRouter are usually actionable — they name the
    affordable token count on a 402, or the retry delay on a 429 — so they are
    passed through rather than replaced with a generic failure string.
    """

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


# --------------------------------------------------------------------------
# credential + model resolution
# --------------------------------------------------------------------------

def _api_key(org=None) -> str:
    """Resolve the OpenRouter key: per-org BYOK first, then .env.

    Mirrors ``engine.core.services.api_key_service.get_api_key`` so the image
    feature honours a key pasted into Settings > Organization > API Keys.
    """
    if org is not None:
        encrypted = getattr(org, 'openrouter_api_key', None)
        if encrypted:
            try:
                from authentication.models import decrypt_value
                raw = decrypt_value(encrypted)
                if raw and raw != encrypted:
                    return raw
            except Exception as exc:  # noqa: BLE001
                logger.warning('BYOK openrouter decrypt failed, using .env: %s', exc)

    key = getattr(settings, 'OPENROUTER_API_KEY', None)
    if not key:
        raise ImageGenerationError(
            'No OpenRouter API key configured. Add one in Settings > '
            'Organization > API Keys, or set OPENROUTER_API_KEY in the '
            'environment.',
            status_code=400,
        )
    return key


def _text_model() -> str:
    return getattr(settings, 'IMAGE_PROMPT_TEXT_MODEL', None) or getattr(
        settings, 'OPENROUTER_INTERNAL_MODEL', 'openai/gpt-5-mini'
    )


def _image_model() -> str:
    return getattr(
        settings, 'IMAGE_RENDER_MODEL', 'google/gemini-2.5-flash-image'
    )


def _model_family(slug: str) -> str:
    """'google', 'openai', or '' — used to pick per-family prompt hedging."""
    return slug.split('/', 1)[0].lower() if '/' in slug else ''


def _headers(api_key: str) -> Dict[str, str]:
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    site = getattr(settings, 'OPENROUTER_SITE_URL', None)
    title = getattr(settings, 'OPENROUTER_SITE_TITLE', None)
    if site:
        headers['HTTP-Referer'] = site
    if title:
        headers['X-Title'] = title
    return headers


def _post(payload: Dict[str, Any], api_key: str, timeout: int) -> Dict[str, Any]:
    """POST to OpenRouter and map failures onto user-facing messages."""
    try:
        response = requests.post(
            OPENROUTER_URL, json=payload, headers=_headers(api_key), timeout=timeout
        )
    except requests.Timeout:
        raise ImageGenerationError(
            f'The model did not respond within {timeout} seconds. Try again, or '
            'pick a faster model.',
            status_code=504,
        )
    except requests.RequestException as exc:
        raise ImageGenerationError(f'Could not reach OpenRouter: {exc}', status_code=502)

    try:
        data = response.json()
    except ValueError:
        raise ImageGenerationError(
            f'OpenRouter returned a non-JSON response (HTTP {response.status_code}).',
            status_code=502,
        )

    error = data.get('error')
    if error:
        # Pass the upstream text through — a 402 names the affordable token
        # count and a 429 names the retry delay, both of which the user can act
        # on. A generic message would hide that.
        message = str(error.get('message') or 'Unknown error from OpenRouter')
        code = error.get('code')
        if code == 402:
            raise ImageGenerationError(
                f'OpenRouter credits exhausted. {message}', status_code=402
            )
        if code == 429:
            raise ImageGenerationError(
                f'Rate limited by the model provider. {message}', status_code=429
            )
        raise ImageGenerationError(message, status_code=502)

    if response.status_code >= 400:
        raise ImageGenerationError(
            f'OpenRouter returned HTTP {response.status_code}.', status_code=502
        )
    return data


# --------------------------------------------------------------------------
# Stage 1 — writing the prompt
# --------------------------------------------------------------------------

def build_prompt_template(
    *,
    article_title: str,
    context_text: str,
    style: str,
    keyword: str = '',
    additional_instructions: str = '',
    image_model: str = '',
) -> str:
    """Assemble the Stage 1 instruction sent to the text model."""
    label, description = STYLES.get(style, STYLES['realistic'])
    family = _model_family(image_model or _image_model())

    if family == 'google':
        target = 'Google\'s Gemini image model'
    elif family == 'openai':
        target = 'OpenAI\'s GPT image model'
    else:
        target = image_model or _image_model()

    keyword_clause = f' (target keyword: "{keyword}")' if keyword else ''

    # This clause is the highest-impact line in the whole template. Without it,
    # abstract or technical passages reliably produce glowing orbs and floating
    # cubes instead of the actual subject matter.
    capture = (
        'Captures the core scene, subject, or concept behind the passage above '
        '(the underlying idea, not the literal wording). If the passage is '
        'abstract or technical (e.g. software, infrastructure, business '
        'process) with nothing literally visual in it, depict its concrete '
        'real-world subject matter directly — e.g. servers, code on a screen, a '
        'dashboard, people at work — rather than inventing an unrelated '
        'metaphor or symbolic scene'
    )

    if additional_instructions:
        instructions_block = (
            '\nAdditional instructions from the user — treat these as required, '
            f'not optional: {additional_instructions}\n'
        )
        incorporate = (
            'Incorporates the user\'s additional instructions above in full'
        )
        # Text rendering is the most common quality complaint. Off by default,
        # but an explicit user request outranks that — and Gemini needs far
        # heavier hedging than OpenAI to avoid placeholder squiggles.
        if family == 'openai':
            text_rule = (
                'Is safe and appropriate for a professional blog. Do not ask '
                'for text, words, or letters to be rendered in the image unless '
                'the additional instructions above call for labels, captions, '
                'or dialogue — in that case choose the exact strings yourself, '
                'write each one inside double quotes, keep it to at most four '
                'words per string and four strings in total, and close the '
                'prompt with "No other text anywhere in the image."'
            )
        else:
            text_rule = (
                'Is safe and appropriate for a professional blog. Do not ask '
                'for text, words, or letters to be rendered in the image unless '
                'the additional instructions above call for labels, captions, '
                'or dialogue — in that case choose the exact strings yourself '
                'and write each one inside double quotes, at most four words '
                'per string and at most four strings in total, say they must be '
                'spelled exactly as written and rendered crisp and legible, '
                'never describe them as placeholder lines, label bars, or '
                'squiggles, and close the prompt with "No other text anywhere '
                'in the image."'
            )
    else:
        instructions_block = ''
        incorporate = 'Reads as a single coherent scene rather than a list of elements'
        text_rule = (
            'Is safe and appropriate for a professional blog, and does not ask '
            'for any text/words/letters to be rendered in the image'
        )

    return f'''You are a prompt engineer writing image-generation prompts for {target}, to illustrate a blog post titled "{article_title}"{keyword_clause}.

Here is the exact passage from the article this image should illustrate:
"""
{context_text}
"""

Desired visual style: {label} — {description}
{instructions_block}
Write ONE detailed, vivid image-generation prompt (2-4 sentences) that:
- {capture}
- Fully commits to the "{label}" style described above
- {incorporate}
- Specifies composition, lighting, mood, and color palette
- {text_rule}
- Is written as a single, ready-to-paste prompt — no headings, no bullet points, no surrounding quotes, no explanation, no preamble

Output ONLY the prompt text.'''


def generate_image_prompt(
    *,
    article_title: str,
    selected_text: str,
    style: str,
    keyword: str = '',
    additional_instructions: str = '',
    org=None,
    user=None,
) -> str:
    """Stage 1: ask a text model to write an image prompt. Returns the prompt."""
    if style not in STYLES:
        raise ImageGenerationError(
            f'Unknown style "{style}". Expected one of: {", ".join(STYLES)}',
            status_code=400,
        )

    image_model = _image_model()
    instruction = build_prompt_template(
        article_title=article_title,
        context_text=selected_text,
        style=style,
        keyword=keyword,
        additional_instructions=additional_instructions,
        image_model=image_model,
    )

    data = _post(
        {
            'model': _text_model(),
            'messages': [{'role': 'user', 'content': instruction}],
            'max_tokens': 500,
        },
        _api_key(org),
        PROMPT_TIMEOUT,
    )

    # Token consumption for the API Keys monitoring screen. Best-effort: a
    # failure here must never fail the generation the user asked for.
    try:
        from .token_usage import record_openrouter_call
        record_openrouter_call(
            getattr(org, 'id', None), user, 'image_prompt', data,
        )
    except Exception:  # noqa: BLE001
        pass

    try:
        prompt = (data['choices'][0]['message'].get('content') or '').strip()
    except (KeyError, IndexError, TypeError):
        raise ImageGenerationError(
            'The model returned an unexpected response shape.', status_code=502
        )

    if not prompt:
        raise ImageGenerationError(
            'The model returned an empty prompt. Try again or rephrase the '
            'selected passage.',
            status_code=502,
        )

    # Models often wrap the answer in quotes or a code fence despite being told
    # not to. Strip both rather than passing them to the renderer as content.
    prompt = re.sub(r'^```[a-z]*\s*|\s*```$', '', prompt).strip()
    prompt = prompt.strip('"').strip()

    return _strip_aspect_ratio_marker(prompt, image_model)


def _strip_aspect_ratio_marker(prompt: str, image_model: str = '') -> str:
    """Remove any trailing ``-ar:...`` marker. Nothing appends one any more.

    Aspect ratio cannot be controlled through OpenRouter at all. Measured
    against ``google/gemini-2.5-flash-image``: a trailing ``-ar:16:9`` marker
    produced 1024x1024, and so did an explicit prose request for a wide
    cinematic 16:9 banner. OpenRouter also exposes no size parameter — no
    image-capable model lists one in ``supported_parameters``, so neither
    Gemini's ``imageConfig.aspectRatio`` nor OpenAI's ``size`` is reachable.

    The marker was therefore doing nothing but adding noise to the prompt, and
    is no longer appended. Stripping still happens because a user may paste a
    prompt carrying one, and for OpenAI models it would be read as literal
    prompt text.

    Images come back square. Do not promise a ratio in the UI; crop client-side
    if a layout needs one.
    """
    return re.sub(r'\s*-ar:\S+\s*$', '', prompt).strip()


def append_brand_colors(prompt: str, colors: Optional[List[str]]) -> str:
    """Re-state the palette on the final prompt so it survives user edits."""
    if not colors:
        return prompt

    parts = [f'{colors[0]} as the dominant color']
    if len(colors) > 1:
        parts.append(f'{colors[1]} as the supporting color')
    if len(colors) > 2:
        parts.append(f'{", ".join(colors[2:])} as accents used sparingly')

    instruction = (
        'Use this brand color palette: ' + ', '.join(parts) +
        '. Keep every other color neutral.'
    )

    # Nothing appends an -ar marker any more, but a pasted prompt may carry
    # one; keep it last if so rather than burying it mid-string.
    match = re.search(r'(\s*-ar:\S+)\s*$', prompt)
    if match:
        return f'{prompt[: match.start()]}\n\n{instruction}{match.group(1)}'
    return f'{prompt}\n\n{instruction}'


# --------------------------------------------------------------------------
# Stage 2 — rendering
# --------------------------------------------------------------------------

def render_image(prompt: str, *, org=None, user=None) -> Tuple[str, bytes]:
    """Stage 2: render ``prompt`` to pixels. Returns (mime_type, raw_bytes)."""
    if not prompt or not prompt.strip():
        raise ImageGenerationError('The prompt is empty.', status_code=400)

    model = _image_model()
    data = _post(
        {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            # Without this the model returns a text *description* of an image
            # rather than an image. It is the whole trick.
            'modalities': ['image', 'text'],
        },
        _api_key(org),
        RENDER_TIMEOUT,
    )

    try:
        from .token_usage import record_openrouter_call
        record_openrouter_call(
            getattr(org, 'id', None), user, 'image_render', data,
        )
    except Exception:  # noqa: BLE001
        pass

    try:
        message = data['choices'][0]['message']
    except (KeyError, IndexError, TypeError):
        raise ImageGenerationError(
            'The model returned an unexpected response shape.', status_code=502
        )

    images = message.get('images') or []
    if not images:
        # A missing images array means the model returned text only — usually a
        # refusal, a model that cannot output images, or a dropped `modalities`.
        # Surface its own words, which normally explain why.
        said = (message.get('content') or '').strip()
        detail = f' It said: "{said[:300]}"' if said else ''
        raise ImageGenerationError(
            f'The model "{model}" returned no image.{detail}', status_code=502
        )

    url = ((images[0] or {}).get('image_url') or {}).get('url') or ''
    if not url.startswith('data:'):
        raise ImageGenerationError(
            'The model returned an image in an unrecognised format.', status_code=502
        )

    try:
        header, payload = url.split(',', 1)
        mime = header[len('data:'):header.index(';')]
        raw = base64.b64decode(payload)
    except Exception:  # noqa: BLE001
        raise ImageGenerationError(
            'Could not decode the image returned by the model.', status_code=502
        )

    if not raw:
        raise ImageGenerationError('The model returned an empty image.', status_code=502)

    return mime, raw


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------

def save_image(raw: bytes, mime: str) -> str:
    """Write bytes under MEDIA_ROOT and return a RELATIVE public URL.

    Relative rather than absolute so the URL survives a domain change and works
    behind a proxy.
    """
    extension = _MIME_EXT.get(mime, 'png')
    directory = Path(settings.MEDIA_ROOT) / 'generated-images'
    directory.mkdir(parents=True, exist_ok=True)

    filename = f'{uuid.uuid4().hex}.{extension}'
    (directory / filename).write_bytes(raw)

    media_url = str(getattr(settings, 'MEDIA_URL', '/media/')).rstrip('/')
    return f'{media_url}/generated-images/{filename}'
