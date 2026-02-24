"""
Email Utility
Uses Django's built-in SMTP email backend (configured via EMAIL_HOST, EMAIL_PORT, etc. in .env)
"""
import logging
from django.core.mail import send_mail as django_send_mail

logger = logging.getLogger(__name__)


def send_mail(subject, message, from_email=None, recipient_list=None, fail_silently=False, html_message=None):
    """
    Send email via Django's SMTP backend.
    Compatible with Django's send_mail signature.

    Uses EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
    EMAIL_USE_TLS, DEFAULT_FROM_EMAIL from settings (loaded from .env).

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
    if not recipient_list:
        error_msg = "No recipients provided"
        logger.error(error_msg)
        if fail_silently:
            return 0
        raise ValueError(error_msg)

    try:
        logger.info(f"Sending email via SMTP to {len(recipient_list)} recipients")

        result = django_send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=fail_silently,
            html_message=html_message,
        )

        if result:
            logger.info(f"Email sent successfully to {recipient_list}")
        else:
            logger.warning(f"Email send returned 0 for {recipient_list}")

        return result

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        if fail_silently:
            return 0
        raise
