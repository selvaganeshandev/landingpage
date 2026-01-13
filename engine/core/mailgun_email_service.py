"""
Mailgun Email Service for Report Delivery
Handles sending emails via Mailgun HTTP API
"""
import logging
import requests
from typing import List, Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class MailgunEmailService:
    """
    Service for sending emails via Mailgun HTTP API.
    Used for report delivery and notifications.
    """

    def __init__(self):
        """Initialize email service with configuration from settings"""
        self.api_key = getattr(settings, 'MAILGUN_API_KEY', '')
        self.domain = getattr(settings, 'MAILGUN_DOMAIN', '')
        self.api_base_url = getattr(
            settings,
            'MAILGUN_API_URL',
            'https://api.mailgun.net/v3'
        )
        self.default_from_email = getattr(
            settings,
            'DEFAULT_FROM_EMAIL',
            'LLM Monitor <noreply@sandbox.mailgun.org>'
        )
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
        self.timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)

    def send_report_email(
        self,
        recipients: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send report email via Mailgun HTTP API.

        Args:
            recipients: List of email addresses
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
            attachments: List of attachment dicts with 'filename' and 'content' (bytes)
            reply_to: Reply-to email address (optional)

        Returns:
            Dict with 'success' (bool), 'message' (str), and 'failed_recipients' (list)
        """
        if not self.api_key or not self.domain:
            logger.error("Mailgun API key or domain not configured in settings")
            return {
                'success': False,
                'message': 'Mailgun API credentials not configured',
                'failed_recipients': recipients
            }

        if not recipients:
            logger.warning("No recipients provided for email")
            return {
                'success': False,
                'message': 'No recipients provided',
                'failed_recipients': []
            }

        try:
            # Build API endpoint
            url = f"{self.api_base_url}/{self.domain}/messages"

            # Build request data
            data = {
                'from': self.default_from_email,
                'to': recipients,
                'subject': subject,
                'text': body_text,
            }

            if body_html:
                data['html'] = body_html

            if reply_to:
                data['h:Reply-To'] = reply_to

            # Prepare files for attachments
            files = []
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content = attachment.get('content')
                    if content:
                        files.append(('attachment', (filename, content)))

            # Make API request
            logger.info(f"Sending email via Mailgun API to {len(recipients)} recipients")

            response = requests.post(
                url,
                auth=('api', self.api_key),
                data=data,
                files=files if files else None,
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info(f"Email sent successfully to {len(recipients)} recipients")
                return {
                    'success': True,
                    'message': f'Email sent successfully to {len(recipients)} recipients',
                    'successful_recipients': recipients,
                    'failed_recipients': []
                }
            else:
                error_msg = response.json().get('message', response.text)
                logger.error(f"Mailgun API error: {response.status_code} - {error_msg}")
                return {
                    'success': False,
                    'message': f'Mailgun API error: {error_msg}',
                    'failed_recipients': recipients
                }

        except requests.exceptions.Timeout:
            logger.error("Mailgun API request timed out")
            return {
                'success': False,
                'message': 'Request timed out',
                'failed_recipients': recipients
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error sending email: {e}")
            return {
                'success': False,
                'message': f'Request error: {str(e)}',
                'failed_recipients': recipients
            }

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'failed_recipients': recipients
            }

    def send_simple_email(
        self,
        recipients: List[str],
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Send a simple text-only email.

        Args:
            recipients: List of email addresses
            subject: Email subject
            body: Email body (plain text)

        Returns:
            Dict with success status and message
        """
        return self.send_report_email(
            recipients=recipients,
            subject=subject,
            body_text=body
        )

