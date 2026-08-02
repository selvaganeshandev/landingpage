"""
DEPRECATED: This notification service is no longer used.
Email notifications are now sent directly from the engine's AlertEvaluator
at engine/core/alert_evaluator.py

This file is kept for reference only.
"""
import logging
from llm_monitor.email_utils import send_mail
from django.conf import settings
from django.utils import timezone
from typing import List
from .models import Alert, AlertNotification, AlertRule
from domains.models import Domain

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending alert notifications through email (Slack/SMS disabled for now)"""
    
    # Define which channels are allowed for each severity level
    # For now, only email is enabled (Slack/SMS disabled)
    SEVERITY_CHANNEL_MAP = {
        'high': ['email'],      # High priority: Email only (SMS/Slack disabled)
        'medium': ['email'],    # Medium priority: Email only
        'low': ['email'],       # Low priority: Email only
    }
    
    @staticmethod
    def send_alert_notifications(alert: Alert, alert_rule: AlertRule) -> None:
        """
        Send notifications for an alert through channels filtered by severity.
        Currently only email is supported (Slack/SMS disabled).
        
        Args:
            alert: The Alert instance
            alert_rule: The AlertRule that triggered this alert
        """
        # Get notification channels from the rule
        requested_channels = alert_rule.notification_channel_list or []
        
        if not requested_channels:
            logger.warning(f"No notification channels configured for alert rule {alert_rule.id}")
            return
        
        # Filter channels based on alert severity (only email allowed for now)
        allowed_channels = NotificationService._filter_channels_by_severity(
            requested_channels=requested_channels,
            alert_severity=alert.severity
        )
        
        if not allowed_channels:
            logger.info(f"No channels allowed for {alert.severity} severity alert {alert.id}")
            return
        
        logger.info(f"Sending notifications for alert {alert.id} (severity: {alert.severity}) "
                   f"through channels: {allowed_channels}")
        
        # Send notifications through each allowed channel (only email for now)
        for channel in allowed_channels:
            try:
                if channel == 'email':
                    NotificationService._send_email_notification(alert, alert_rule)
                # Slack and SMS disabled for now
                # elif channel == 'slack':
                #     NotificationService._send_slack_notification(alert, alert_rule)
                # elif channel == 'sms':
                #     NotificationService._send_sms_notification(alert, alert_rule)
            except Exception as e:
                logger.error(f"Error sending {channel} notification for alert {alert.id}: {str(e)}", exc_info=True)
    
    @staticmethod
    def _filter_channels_by_severity(
        requested_channels: List[str],
        alert_severity: str
    ) -> List[str]:
        """
        Filter notification channels based on alert severity.
        Currently only email is enabled.
        
        Args:
            requested_channels: Channels requested in the alert rule
            alert_severity: Alert severity ('high', 'medium', 'low')
        
        Returns:
            List of allowed channels for this severity (only 'email' for now)
        """
        # Get allowed channels for this severity
        allowed_channels = NotificationService.SEVERITY_CHANNEL_MAP.get(
            alert_severity,
            ['email']  # Default to email only
        )
        
        # Return intersection: only channels that are both requested AND allowed
        filtered_channels = [
            channel for channel in requested_channels 
            if channel in allowed_channels
        ]
        
        # Log if any channels were filtered out
        filtered_out = set(requested_channels) - set(filtered_channels)
        if filtered_out:
            logger.info(
                f"Filtered out channels {filtered_out} for {alert_severity} severity alert. "
                f"Only email is enabled. Allowed channels: {filtered_channels}"
            )
        
        return filtered_channels
    
    @staticmethod
    def _send_email_notification(alert: Alert, alert_rule: AlertRule) -> None:
        """Send email notification"""
        # Get email from AlertConfiguration
        try:
            from .models import AlertConfiguration
            
            # Try to get email from AlertConfiguration for the domain
            config = AlertConfiguration.objects.filter(domain_id=alert.domain_id).first()
            
            if config and config.email_enabled and config.email_address_list:
                email_addresses = config.email_address_list
            else:
                # Fallback to domain's organisation admins
                domain = alert.domain
                org_admins = domain.organisation.account_set.filter(role__in=['admin', 'super_admin'])
                
                if org_admins.exists():
                    email_addresses = list(org_admins.values_list('email', flat=True))
                else:
                    # Final fallback to default
                    email_addresses = [settings.DEFAULT_FROM_EMAIL]
        except Exception as e:
            logger.warning(f"Error getting email addresses for domain {alert.domain_id}: {str(e)}")
            email_addresses = [settings.DEFAULT_FROM_EMAIL]
        
        subject = f"[{alert.severity.upper()}] {alert.title}"
        message = f"""
Alert Details:
--------------
Title: {alert.title}
Message: {alert.message}
Severity: {alert.severity}
Platform: {alert.platform or 'All Platforms'}
Domain: {alert.domain.name}
Metric: {alert.metric}
Status: {alert.status}

Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

View in dashboard: {settings.FRONTEND_URL}/alerts
"""
        
        for email_address in email_addresses:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email_address],
                    fail_silently=False
                )
                
                AlertNotification.objects.create(
                    alert=alert,
                    channel='email',
                    recipient=email_address,
                    status='sent'
                )
                
                logger.info(f"Email notification sent for alert {alert.id} to {email_address}")
            except Exception as e:
                AlertNotification.objects.create(
                    alert=alert,
                    channel='email',
                    recipient=email_address,
                    status='failed',
                    error_message=str(e)
                )
                logger.error(f"Failed to send email notification for alert {alert.id} to {email_address}: {str(e)}")
