"""
Mailgun Email Service for Report Delivery
Handles sending emails via Mailgun SMTP
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class MailgunEmailService:
    """
    Service for sending emails via Mailgun SMTP.
    Used for report delivery and notifications.
    """

    def __init__(self):
        """Initialize email service with configuration from settings"""
        self.email_host = getattr(settings, 'EMAIL_HOST', 'smtp.mailgun.org')
        self.email_port = getattr(settings, 'EMAIL_PORT', 587)
        self.email_use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        self.email_host_user = getattr(settings, 'EMAIL_HOST_USER', '')
        self.email_host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.default_from_email = getattr(
            settings, 
            'DEFAULT_FROM_EMAIL', 
            'LLM Monitor <noreply@sandbox.mailgun.org>'
        )
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
        self.email_timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)

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
        Send report email via Mailgun SMTP.

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
        if not self.email_host_user or not self.email_host_password:
            logger.error("Email credentials not configured in settings")
            return {
                'success': False,
                'message': 'Email credentials not configured',
                'failed_recipients': recipients
            }

        if not recipients:
            logger.warning("No recipients provided for email")
            return {
                'success': False,
                'message': 'No recipients provided',
                'failed_recipients': []
            }

        failed_recipients = []
        successful_recipients = []

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.default_from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject

            if reply_to:
                msg['Reply-To'] = reply_to

            # Add text part
            text_part = MIMEText(body_text, 'plain')
            msg.attach(text_part)

            # Add HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, 'html')
                msg.attach(html_part)

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    filename = attachment.get('filename', 'attachment')
                    content = attachment.get('content')
                    content_type = attachment.get('content_type', 'application/octet-stream')

                    if content:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}"'
                        )
                        msg.attach(part)

            # Connect to SMTP server and send
            logger.info(f"Connecting to SMTP server {self.email_host}:{self.email_port}")
            with smtplib.SMTP(self.email_host, self.email_port, timeout=self.email_timeout) as server:
                if self.email_use_tls:
                    logger.debug("Starting TLS...")
                    server.starttls()

                logger.debug(f"Logging in as {self.email_host_user}")
                server.login(self.email_host_user, self.email_host_password)

                # Send to all recipients
                logger.info(f"Sending email to {len(recipients)} recipients")
                server.send_message(msg, to_addrs=recipients)
                successful_recipients = recipients

                logger.info(f"Email sent successfully to {len(successful_recipients)} recipients")

            return {
                'success': True,
                'message': f'Email sent successfully to {len(successful_recipients)} recipients',
                'successful_recipients': successful_recipients,
                'failed_recipients': failed_recipients
            }

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            return {
                'success': False,
                'message': f'SMTP Authentication failed: {str(e)}',
                'failed_recipients': recipients
            }

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return {
                'success': False,
                'message': f'SMTP error: {str(e)}',
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

