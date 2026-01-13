"""
Mailgun HTTP API Email Utility
Provides send_mail function compatible with Django's interface
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_mail(subject, message, from_email=None, recipient_list=None, fail_silently=False, html_message=None):
    """
    Send email via Mailgun HTTP API.
    Compatible with Django's send_mail signature.

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
    api_url = getattr(settings, 'MAILGUN_API_URL', 'https://api.mailgun.net/v3')
    timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)

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

    try:
        url = f"{api_url}/{domain}/messages"

        data = {
            'from': from_email,
            'to': recipient_list,
            'subject': subject,
            'text': message,
        }

        if html_message:
            data['html'] = html_message

        logger.info(f"Sending email via Mailgun API to {len(recipient_list)} recipients")

        response = requests.post(
            url,
            auth=('api', api_key),
            data=data,
            timeout=timeout
        )

        if response.status_code == 200:
            logger.info(f"Email sent successfully to {recipient_list}")
            return 1
        else:
            error_msg = response.json().get('message', response.text)
            logger.error(f"Mailgun API error: {response.status_code} - {error_msg}")
            if fail_silently:
                return 0
            raise Exception(f"Mailgun API error: {error_msg}")

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
        logger.error(f"Unexpected error sending email: {e}")
        if fail_silently:
            return 0
        raise
