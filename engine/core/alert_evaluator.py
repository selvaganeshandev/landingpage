"""
Alert Evaluator - Checks alert rules and creates alerts with email notifications
Designed to be called from processing engines with current metrics
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decimal import Decimal
from typing import Optional, Dict, Any, List
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """
    Evaluates alert rules and creates alerts with email notifications.
    Designed to be integrated into existing processors.
    """

    def __init__(self, domain):
        """
        Initialize evaluator for a domain.

        Args:
            domain: Domain instance
        """
        self.domain = domain
        self.alerts_created = []

    def evaluate_all_rules(self, metrics: Dict[str, Any]) -> List:
        """
        Evaluate all enabled alert rules for this domain.

        Args:
            metrics: Dict containing current and previous metrics
                {
                    'visibility_score': 75.5,
                    'previous_visibility_score': 85.0,
                    'sentiment_score': 65.0,
                    'previous_sentiment_score': 70.0,
                    'negative_sentiment_percent': 15.0,
                    'previous_negative_sentiment_percent': 8.0,
                    'average_position': 3.5,
                    'previous_average_position': 2.0,
                    'total_mentions': 150,
                    'previous_total_mentions': 100,
                    'time_window_hours': 168,  # 7 days
                }

        Returns:
            List of created Alert instances
        """
        # Import here to avoid circular imports
        from shared_models.models import AlertRule

        # Get enabled rules for this domain
        rules = AlertRule.objects.filter(
            domain=self.domain,
            enabled=True
        )

        if not rules.exists():
            logger.debug(f"No enabled alert rules for domain {self.domain.name}")
            return []

        logger.info(f"Evaluating {rules.count()} alert rules for domain {self.domain.name}")

        for rule in rules:
            try:
                alert = self._evaluate_single_rule(rule, metrics)
                if alert:
                    self.alerts_created.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id} ({rule.name}): {e}", exc_info=True)

        return self.alerts_created

    def _evaluate_single_rule(self, rule, metrics: Dict[str, Any]) -> Optional:
        """Evaluate a single alert rule"""
        conditions = rule.conditions or {}
        trigger_type = conditions.get('trigger_type')

        if not trigger_type:
            logger.warning(f"Rule {rule.id} has no trigger_type")
            return None

        # Route to appropriate evaluator
        evaluators = {
            'visibility_drop': self._check_visibility_drop,
            'visibility_increase': self._check_visibility_increase,
            'sentiment_negative': self._check_sentiment_negative,
            'sentiment_positive': self._check_sentiment_positive,
            'position_drop': self._check_position_drop,
            'mention_spike': self._check_mention_spike,
        }

        evaluator = evaluators.get(trigger_type)
        if not evaluator:
            logger.warning(f"No evaluator for trigger_type: {trigger_type}")
            return None

        return evaluator(rule, metrics)

    def _check_visibility_drop(self, rule, metrics: Dict) -> Optional:
        """Check if visibility dropped below threshold"""
        current = metrics.get('visibility_score', 0)
        previous = metrics.get('previous_visibility_score', 0)

        if previous == 0:
            return None  # Can't calculate percentage change

        # Calculate percentage change
        change_percent = ((current - previous) / previous) * 100
        threshold = rule.conditions.get('threshold_percent', 10)

        if change_percent < -threshold:  # Dropped by more than threshold
            severity = self._determine_severity(abs(change_percent), threshold)

            return self._create_alert(
                rule=rule,
                alert_type='visibility_drop',
                severity=severity,
                title=f'Visibility Dropped by {abs(change_percent):.1f}%',
                message=f'Brand visibility for {self.domain.name} decreased from {previous:.1f} to {current:.1f} ({change_percent:.1f}% drop) over {metrics.get("time_window_hours", 168)} hours.',
                metric=Decimal(str(change_percent))
            )

        return None

    def _check_visibility_increase(self, rule, metrics: Dict) -> Optional:
        """Check if visibility increased above threshold"""
        current = metrics.get('visibility_score', 0)
        previous = metrics.get('previous_visibility_score', 0)

        if previous == 0:
            return None

        change_percent = ((current - previous) / previous) * 100
        threshold = rule.conditions.get('threshold_percent', 15)

        if change_percent > threshold:
            severity = 'low'  # Good news = low severity

            return self._create_alert(
                rule=rule,
                alert_type='visibility_drop',  # Use same type, positive metric
                severity=severity,
                title=f'Visibility Increased by {change_percent:.1f}%',
                message=f'Brand visibility for {self.domain.name} increased from {previous:.1f} to {current:.1f} ({change_percent:.1f}% gain) over {metrics.get("time_window_hours", 168)} hours.',
                metric=Decimal(str(change_percent))
            )

        return None

    def _check_sentiment_negative(self, rule, metrics: Dict) -> Optional:
        """Check if negative sentiment spiked"""
        current_negative = metrics.get('negative_sentiment_percent', 0)
        previous_negative = metrics.get('previous_negative_sentiment_percent', 0)

        change = current_negative - previous_negative
        threshold = rule.conditions.get('threshold_percent', 10)

        if change > threshold:
            severity = self._determine_severity(change, threshold)

            return self._create_alert(
                rule=rule,
                alert_type='sentiment_negative',
                severity=severity,
                title=f'Negative Sentiment Increased by {change:.1f}%',
                message=f'Negative sentiment for {self.domain.name} increased from {previous_negative:.1f}% to {current_negative:.1f}% over {metrics.get("time_window_hours", 168)} hours.',
                metric=Decimal(str(change))
            )

        return None

    def _check_sentiment_positive(self, rule, metrics: Dict) -> Optional:
        """Check if positive sentiment increased"""
        current = metrics.get('sentiment_score', 0)
        previous = metrics.get('previous_sentiment_score', 0)

        if previous == 0:
            return None

        change_percent = ((current - previous) / previous) * 100
        threshold = rule.conditions.get('threshold_percent', 15)

        if change_percent > threshold:
            severity = 'low'  # Good news

            return self._create_alert(
                rule=rule,
                alert_type='sentiment_negative',  # Use same type
                severity=severity,
                title=f'Sentiment Improved by {change_percent:.1f}%',
                message=f'Sentiment score for {self.domain.name} increased from {previous:.1f} to {current:.1f} ({change_percent:.1f}% improvement) over {metrics.get("time_window_hours", 168)} hours.',
                metric=Decimal(str(change_percent))
            )

        return None

    def _check_position_drop(self, rule, metrics: Dict) -> Optional:
        """Check if average position worsened"""
        current = metrics.get('average_position', 0)
        previous = metrics.get('previous_average_position', 0)

        if previous == 0 or current == 0:
            return None

        # For position, lower is better (position 1 is best)
        # So increase in position number = worse
        change = current - previous
        threshold = rule.conditions.get('threshold_percent', 20)  # % of position change

        if previous > 0:
            change_percent = (change / previous) * 100
        else:
            change_percent = 0

        if change > 0 and change_percent > threshold:  # Position worsened
            severity = self._determine_severity(change_percent, threshold)

            return self._create_alert(
                rule=rule,
                alert_type='position_loss',
                severity=severity,
                title=f'Position Dropped from {previous:.1f} to {current:.1f}',
                message=f'Average position for {self.domain.name} worsened from {previous:.1f} to {current:.1f} ({change_percent:.1f}% drop) over {metrics.get("time_window_hours", 168)} hours.',
                metric=Decimal(str(change_percent))
            )

        return None

    def _check_mention_spike(self, rule, metrics: Dict) -> Optional:
        """Check if mention volume spiked"""
        current = metrics.get('total_mentions', 0)
        previous = metrics.get('previous_total_mentions', 0)

        if previous == 0:
            return None

        change_percent = ((current - previous) / previous) * 100
        threshold = rule.conditions.get('threshold_percent', 30)

        if change_percent > threshold:
            severity = 'low'  # Good news usually

            return self._create_alert(
                rule=rule,
                alert_type='visibility_drop',  # Reuse visibility_drop type
                severity=severity,
                title=f'Mention Volume Spiked by {change_percent:.1f}%',
                message=f'Total mentions for {self.domain.name} increased from {previous} to {current} ({change_percent:.1f}% spike) over {metrics.get("time_window_hours", 168)} hours.',
                metric=Decimal(str(change_percent))
            )

        return None

    def _determine_severity(self, change_value: float, threshold: float) -> str:
        """
        Determine alert severity based on how much threshold was exceeded.

        Args:
            change_value: Actual change value (absolute)
            threshold: Alert rule threshold

        Returns:
            'high', 'medium', or 'low'
        """
        if change_value > threshold * 3:
            return 'high'
        elif change_value > threshold * 2:
            return 'medium'
        else:
            return 'low'

    @transaction.atomic
    def _create_alert(self, rule, alert_type: str, severity: str,
                     title: str, message: str, metric: Decimal) -> Optional:
        """
        Create alert and trigger notification.

        Args:
            rule: AlertRule instance
            alert_type: Alert type (visibility_drop, etc.)
            severity: 'high', 'medium', or 'low'
            title: Alert title
            message: Alert message
            metric: Metric value (percentage change)

        Returns:
            Created Alert instance or None
        """
        # Import here to avoid circular imports
        from shared_models.models import Alert

        # Check for duplicate recent alerts (avoid spam)
        from datetime import timedelta
        recent_cutoff = timezone.now() - timedelta(hours=24)

        duplicate = Alert.objects.filter(
            domain=self.domain,
            type=alert_type,
            status='active',
            created_at__gte=recent_cutoff,
            title=title
        ).first()

        if duplicate:
            logger.info(f"Skipping duplicate alert: {title}")
            return None

        # Create alert
        alert = Alert.objects.create(
            domain=self.domain,
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            platform=None,  # Overall, not platform-specific
            metric=metric,
            status='active',
            created_by=None  # System-generated
        )

        # Update rule statistics
        rule.detection_count = (rule.detection_count or 0) + 1
        rule.last_triggered_at = timezone.now()
        rule.save(update_fields=['detection_count', 'last_triggered_at'])

        logger.info(f"Created alert {alert.id}: {title} (severity: {severity})")

        # Send email notification
        try:
            self._send_email_notification(alert, rule)
            logger.info(f"Email notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send email notification for alert {alert.id}: {e}", exc_info=True)

        return alert

    def _send_email_notification(self, alert, rule) -> None:
        """
        Send email notification using SMTP directly.

        Args:
            alert: Alert instance
            rule: AlertRule instance
        """
        from shared_models.models import AlertNotification, AlertConfiguration

        # Get notification channels from the rule
        requested_channels = rule.notification_channel_list or []

        if 'email' not in requested_channels:
            logger.debug(f"Email not in notification channels for alert rule {rule.id}")
            return

        # Get email configuration from environment
        email_host = os.getenv('EMAIL_HOST', 'smtp.mailgun.org')
        email_port = int(os.getenv('EMAIL_PORT', 587))
        email_use_tls = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
        email_host_user = os.getenv('EMAIL_HOST_USER', '')
        email_host_password = os.getenv('EMAIL_HOST_PASSWORD', '')
        default_from_email = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')
        email_timeout = int(os.getenv('EMAIL_TIMEOUT', 10))

        if not email_host_user or not email_host_password:
            logger.error("Email credentials not configured in environment variables")
            return

        # Get recipient email addresses
        try:
            # Try to get email from AlertConfiguration for the domain
            config = AlertConfiguration.objects.filter(domain=self.domain).first()

            if config and config.email_enabled and config.email_address:
                email_addresses = [config.email_address]
            else:
                # Fallback to domain's organisation admins
                org_admins = self.domain.organisation.account_set.filter(
                    role__in=['admin', 'super_admin']
                )

                if org_admins.exists():
                    email_addresses = list(org_admins.values_list('email', flat=True))
                else:
                    # Final fallback - use default from email
                    logger.warning(f"No email recipients found for domain {self.domain.name}")
                    email_addresses = [default_from_email]
        except Exception as e:
            logger.error(f"Error getting email addresses for domain {self.domain.id}: {e}")
            email_addresses = [default_from_email]

        # Prepare email content
        subject = f"[{alert.severity.upper()}] {alert.title}"
        body = f"""
Alert Details:
--------------
Title: {alert.title}
Message: {alert.message}
Severity: {alert.severity}
Platform: {alert.platform or 'All Platforms'}
Domain: {self.domain.name}
Metric: {alert.metric}
Status: {alert.status}

Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}

View in dashboard: {frontend_url}/alerts
"""

        # Send email to each recipient
        for recipient in email_addresses:
            try:
                # Create message
                msg = MIMEMultipart()
                msg['From'] = default_from_email
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                # Connect to SMTP server and send
                with smtplib.SMTP(email_host, email_port, timeout=email_timeout) as server:
                    if email_use_tls:
                        server.starttls()
                    server.login(email_host_user, email_host_password)
                    server.send_message(msg)

                # Record successful notification
                AlertNotification.objects.create(
                    alert=alert,
                    channel='email',
                    recipient=recipient,
                    status='sent'
                )

                logger.info(f"Email sent to {recipient} for alert {alert.id}")

            except Exception as e:
                # Record failed notification
                AlertNotification.objects.create(
                    alert=alert,
                    channel='email',
                    recipient=recipient,
                    status='failed',
                    error_message=str(e)
                )
                logger.error(f"Failed to send email to {recipient} for alert {alert.id}: {e}")
