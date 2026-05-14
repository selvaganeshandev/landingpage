import logging
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import Domain


logger = logging.getLogger(__name__)


def schedule_domain_processing(domain: Domain) -> bool:
    """
    Schedule initial processing for a domain via the engine service.

    Returns True if the scheduling call succeeded, False otherwise.
    """
    engine_api_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001').rstrip('/')
    start_endpoint = f"{engine_api_url}/api/start/"

    payload = {
        'domain_id': domain.id,
        'sync': False,  # Process async - will be picked up by start_processor daemon
    }

    # Check if domain has keywords before scheduling
    from keywords.models import Keyword
    has_keywords = Keyword.objects.filter(domain=domain).exists()
    
    if not has_keywords:
        logger.warning("Domain %s has no keywords - cannot schedule processing", domain.id)
        domain.processing_status = 'INIT'
        domain.track_message = 'No keywords found. Please add keywords before processing.'
        domain.save(update_fields=['processing_status', 'track_message', 'modified_at'])
        return False

    # Mark as scheduled - processing loop will pick it up automatically
    with transaction.atomic():
        domain.refresh_from_db()
        domain.processing_status = 'SCHD'
        domain.track_message = 'Queued for initial processing'
        domain.tracked_at = timezone.now()
        domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])

    # Try to notify engine API (optional - processing loop will handle it anyway)
    try:
        response = requests.post(start_endpoint, json=payload, timeout=5)
        response.raise_for_status()
        logger.info("Notified engine API for domain %s processing", domain.id)
        return True
    except requests.RequestException as exc:
        # API call failed, but that's OK - processing loop will pick up SCHD domains automatically
        logger.warning("Engine API notification failed for domain %s (processing loop will handle it): %s", domain.id, exc)
        # Domain is already in SCHD status, so processing loop will pick it up
        return True  # Return True because domain is scheduled (even if API call failed)

