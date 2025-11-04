from django.db import models
from domains.models import Domain
from authentication.models import Account


class Integration(models.Model):
    INTEGRATION_TYPES = [
        ('google_analytics', 'Google Analytics'),
        ('search_console', 'Google Search Console'),
        ('slack', 'Slack'),
        ('sms', 'SMS Provider'),
        ('cms', 'CMS'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('error', 'Error'),
        ('disconnected', 'Disconnected'),
    ]
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='integrations')
    type = models.CharField(max_length=50, choices=INTEGRATION_TYPES)
    provider_id = models.CharField(max_length=255)  # GA property ID, GSC URL, etc.
    credentials = models.JSONField(default=dict)  # Encrypted OAuth tokens
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_sync_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='integrations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'integrations'
        unique_together = [['domain', 'type', 'provider_id']]
        indexes = [
            models.Index(fields=['domain', 'type']),
            models.Index(fields=['status', 'last_sync_at']),
            # Additional indexes
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['last_sync_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.domain.name} - {self.get_type_display()}"

