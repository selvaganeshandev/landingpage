"""AI-generated-text detection via the Hugging Face inference router.

One place for the call so the interactive endpoint (content.views
.detect_ai_content) and the batch command (detect_ai_drafts) agree on the
model, the truncation window and how a result lands on GeneratedContent.
"""
import logging
import re

import requests
from decouple import config

from django.utils import timezone

logger = logging.getLogger(__name__)

MODEL_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "Hello-SimpleAI/chatgpt-detector-roberta"
)
MIN_CHARS = 50
# RoBERTa accepts 514 tokens; ~3 chars per token keeps us safely under it.
MAX_CHARS = 1500
REQUEST_TIMEOUT = 30
AI_LABELS = {'fake', 'chatgpt', 'ai', 'gpt'}
HUMAN_LABELS = {'real', 'human'}


class AIDetectionError(Exception):
    """The detector could not produce a score.

    `status_code` is the HTTP status the API endpoint should answer with.
    """

    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.status_code = status_code


class AIDetectionModelLoading(AIDetectionError):
    """Hugging Face is cold-starting the model; retry after `estimated_time`."""

    def __init__(self, estimated_time=20):
        super().__init__(
            'AI detection model is loading. Please try again in a few seconds.',
            503,
        )
        self.estimated_time = estimated_time


def strip_html_tags(html_content):
    """Strip HTML tags and collapse whitespace."""
    if not html_content:
        return ""
    clean = re.sub(r'<[^>]+>', '', html_content)
    return re.sub(r'\s+', ' ', clean).strip()


def detect_ai_text(text):
    """Score `text` (plain or HTML) with the ChatGPT-detector model.

    Returns {'ai_score', 'human_score', 'label', 'confidence',
    'text_analyzed_length'}; scores are 0-100. Raises AIDetectionError (or
    its AIDetectionModelLoading subclass) when no score can be produced.
    """
    plain_text = strip_html_tags(text)
    if len(plain_text) < MIN_CHARS:
        raise AIDetectionError(
            'Text must be at least 50 characters for accurate detection', 400
        )
    plain_text = plain_text[:MAX_CHARS]

    hf_api_key = config('HUGGINGFACE_API_KEY', default='')
    if not hf_api_key:
        raise AIDetectionError(
            'Hugging Face API key not configured. Please add HUGGINGFACE_API_KEY '
            'to your environment.',
            500,
        )

    try:
        response = requests.post(
            MODEL_URL,
            headers={
                "Authorization": f"Bearer {hf_api_key}",
                "Content-Type": "application/json",
            },
            json={"inputs": plain_text},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        raise AIDetectionError(
            'AI detection service timed out. Please try again.', 504
        )

    if response.status_code == 503:
        try:
            estimated = response.json().get('estimated_time', 20)
        except ValueError:
            estimated = 20
        raise AIDetectionModelLoading(estimated)

    if not response.ok:
        logger.error(
            "Hugging Face API error: %s - %s", response.status_code, response.text
        )
        raise AIDetectionError(
            f'AI detection service error: {response.text}', 500
        )

    result = response.json()
    # Shape: [[{"label": "ChatGPT", "score": 0.9}, {"label": "Human", "score": 0.1}]]
    if not (isinstance(result, list) and result):
        logger.error("Unexpected response format from Hugging Face: %s", result)
        raise AIDetectionError('Unexpected response from AI detection service', 500)
    classifications = result[0] if isinstance(result[0], list) else result

    ai_score = 0
    human_score = 0
    for item in classifications:
        label = str(item.get('label', '')).lower()
        score = item.get('score', 0) * 100
        if label in AI_LABELS:
            ai_score = score
        elif label in HUMAN_LABELS:
            human_score = score

    if ai_score > human_score:
        label, confidence = "AI-generated", ai_score
    else:
        label, confidence = "Human-written", human_score

    return {
        'ai_score': ai_score,
        'human_score': human_score,
        'label': label,
        'confidence': confidence,
        'text_analyzed_length': len(plain_text),
    }


def save_detection(content_obj, result):
    """Persist a detect_ai_text() result on a GeneratedContent row."""
    content_obj.ai_detection_score = round(result['ai_score'], 2)
    content_obj.human_detection_score = round(result['human_score'], 2)
    content_obj.ai_detection_label = result['label']
    content_obj.ai_detection_checked_at = timezone.now()
    content_obj.save(update_fields=[
        'ai_detection_score', 'human_detection_score',
        'ai_detection_label', 'ai_detection_checked_at',
    ])
    return content_obj.ai_detection_checked_at
