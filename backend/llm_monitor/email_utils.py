"""
Email Utility — Mailgun HTTP API
Sends emails via Mailgun's REST API (faster & more reliable than SMTP).
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_mail(subject, message, from_email=None, recipient_list=None, fail_silently=False, html_message=None):
    """
    Send email via Mailgun HTTP API.
    Compatible with Django's send_mail signature.

    Requires MAILGUN_API_KEY and MAILGUN_DOMAIN in settings (loaded from .env).

    Args:
        subject: Email subject
        message: Plain text email body
        from_email: Sender email (defaults to settings.DEFAULT_FROM_EMAIL)
        recipient_list: List of recipient email addresses
        fail_silently: If True, suppress exceptions
        html_message: Optional HTML email body

    Returns:
        1 if successful, 0 if failed
    """
    api_key = getattr(settings, 'MAILGUN_API_KEY', '')
    domain = getattr(settings, 'MAILGUN_DOMAIN', '')

    if not api_key or not domain:
        error_msg = "Mailgun API key or domain not configured"
        logger.error(error_msg)
        if fail_silently:
            return 0
        raise ValueError(error_msg)

    if not recipient_list:
        error_msg = "No recipients provided"
        logger.error(error_msg)
        if fail_silently:
            return 0
        raise ValueError(error_msg)

    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '')

    timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)

    try:
        url = f"https://api.mailgun.net/v3/{domain}/messages"

        data = {
            'from': from_email,
            'to': recipient_list,
            'subject': subject,
            'text': message,
        }

        if html_message:
            data['html'] = html_message

        logger.info(f"Sending email via Mailgun API to {recipient_list}")

        response = requests.post(
            url,
            auth=('api', api_key),
            data=data,
            timeout=timeout,
        )

        if response.status_code == 200:
            logger.info(f"Email sent successfully to {recipient_list}")
            return 1
        else:
            # Try to parse JSON error, fallback to raw text
            try:
                error_msg = response.json().get('message', response.text)
            except (ValueError, KeyError):
                error_msg = response.text[:500]
            logger.error(f"Mailgun API error: {response.status_code} - {error_msg}")
            if fail_silently:
                return 0
            raise Exception(f"Mailgun API error ({response.status_code}): {error_msg}")

    except requests.exceptions.Timeout:
        error_msg = "Mailgun API request timed out"
        logger.error(error_msg)
        if fail_silently:
            return 0
        raise Exception(error_msg)

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error sending email: {e}")
        if fail_silently:
            return 0
        raise

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        if fail_silently:
            return 0
        raise
