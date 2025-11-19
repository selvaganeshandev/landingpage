import logging
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

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

    # Optimistically mark as scheduled before making remote call
    domain.processing_status = 'SCHD'
    domain.track_message = 'Queued for initial processing'
    domain.tracked_at = timezone.now()
    domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])

    try:
        response = requests.post(start_endpoint, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Scheduled domain %s for processing via engine", domain.id)
        return True
    except requests.RequestException as exc:
        logger.error("Failed to schedule processing for domain %s: %s", domain.id, exc)
        # Revert status so it can be retried later
        domain.processing_status = 'INIT'
        domain.track_message = f'Failed to schedule processing: {exc}'
        domain.save(update_fields=['processing_status', 'track_message', 'modified_at'])
        return False

