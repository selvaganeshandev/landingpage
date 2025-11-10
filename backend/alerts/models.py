from django.db import models
from django.contrib.postgres.fields import ArrayField
from domains.models import Domain
from authentication.models import Account


class Alert(models.Model):
    ALERT_TYPES = [
        ('visibility_drop', 'Visibility Drop'),
        ('sentiment_negative', 'Negative Sentiment'),
        ('competitor_surge', 'Competitor Surge'),
        ('anomaly', 'Anomaly'),
        ('position_loss', 'Position Loss'),
        ('new_platform', 'New Platform'),
        ('misinformation', 'Misinformation'),
    ]
    
    SEVERITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
    ]
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='alerts')
    type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    platform = models.CharField(max_length=100, null=True, blank=True)
    metric = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='alerts_created')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'alerts'
        indexes = [
            models.Index(fields=['domain', 'status', 'created_at']),
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['type', 'created_at']),
            # Additional indexes
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['domain', 'type', 'status']),
            models.Index(fields=['resolved_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.severity}"


class AlertRule(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='alert_rules')
    name = models.CharField(max_length=255)
    description = models.TextField()
    enabled = models.BooleanField(default=True)
    conditions = models.JSONField(default=dict)
    notification_channel_list = models.JSONField(default=list, blank=True)  # ['email', 'slack', 'sms']
    detection_count = models.IntegerField(default=0)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='alert_rules_created')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'alert_rules'
        indexes = [
            models.Index(fields=['domain', 'enabled']),
            # Additional indexes
            models.Index(fields=['enabled', 'last_triggered_at']),
            models.Index(fields=['domain', '-detection_count']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class AlertNotification(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('sms', 'SMS'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notifications')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'alert_notifications'
        indexes = [
            models.Index(fields=['alert', 'sent_at']),
            models.Index(fields=['status', 'sent_at']),
            # Additional indexes
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['recipient', '-sent_at']),
        ]
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.channel} to {self.recipient} - {self.status}"


class AlertConfiguration(models.Model):
    """Store alert configuration settings per domain or organization"""
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='alert_config', null=True, blank=True)
    organisation = models.ForeignKey('authentication.Organisation', on_delete=models.CASCADE, related_name='alert_config', null=True, blank=True)
    
    # General Settings
    alerts_enabled = models.BooleanField(default=True)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)  # e.g., "22:00"
    quiet_hours_end = models.TimeField(null=True, blank=True)    # e.g., "08:00"
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('realtime', 'Real-time'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='realtime'
    )
    
    # Email Settings
    email_enabled = models.BooleanField(default=True)
    email_address = models.EmailField(null=True, blank=True)
    
    # Slack Settings
    slack_enabled = models.BooleanField(default=False)
    slack_channel = models.CharField(max_length=100, null=True, blank=True)  # e.g., "#ai-monitoring"
    slack_webhook_url = models.URLField(null=True, blank=True)  # Slack webhook URL
    
    # SMS Settings
    sms_enabled = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, null=True, blank=True)  # e.g., "+15550000000"
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'alert_configurations'
        constraints = [
            models.UniqueConstraint(fields=['domain'], condition=models.Q(domain__isnull=False), name='unique_domain_config'),
            models.UniqueConstraint(fields=['organisation'], condition=models.Q(organisation__isnull=False), name='unique_org_config'),
        ]
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['organisation']),
        ]
    
    def __str__(self):
        scope = f"Domain: {self.domain.name}" if self.domain else f"Org: {self.organisation.name}"
        return f"Alert Config - {scope}"

