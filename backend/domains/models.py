from django.db import models


class Domain(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]

    MISINFO_SCAN_STATUS_CHOICES = [
        ('NOT_READY', 'Not Ready'),      # No prompt analytics data yet
        ('READY', 'Ready'),               # Has data, ready to scan
        ('SCANNING', 'Scanning'),         # Scan in progress
        ('SCANNED', 'Scanned'),           # Scan completed
        ('NO_ISSUES', 'No Issues Found'), # Scan completed with no alerts
    ]
    """
    Domain model representing websites or domains being monitored
    """
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    name = models.CharField(max_length=255, help_text="Name of the domain")
    url = models.URLField(help_text="URL of the domain")
    short_description = models.CharField(max_length=500, blank=True, null=True, help_text="Brief description of the brand/domain")

    # Content Guidelines fields
    tone_of_voice = models.TextField(blank=True, null=True, help_text="Brand's tone of voice guidelines")
    content_style = models.TextField(blank=True, null=True, help_text="Preferred content style guidelines")
    key_messages = models.TextField(blank=True, null=True, help_text="Key messages or themes to emphasize")
    topics_to_avoid = models.TextField(blank=True, null=True, help_text="Topics or themes to avoid in content")

    # Brand Identity fields
    target_audience = models.TextField(blank=True, null=True, help_text="Target audience demographics and preferences")
    brand_values = models.TextField(blank=True, null=True, help_text="Brand's core values")
    key_competitors = models.TextField(blank=True, null=True, help_text="Main competitors")

    country = models.CharField(max_length=100, default='United States', help_text="Country name for domain context")
    niches = models.JSONField(blank=True, null=True, help_text="List of industry niches/categories for the brand")
    organisation = models.ForeignKey(
        'authentication.Organisation',
        on_delete=models.CASCADE,
        related_name='domains',
        help_text="Organisation this domain belongs to"
    )
    total_mentions = models.PositiveIntegerField(default=0, help_text="Total number of mentions")
    total_citations = models.PositiveIntegerField(default=0, help_text="Total number of citations")
    visibility_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Visibility score of the domain"
    )
    average_position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Average position in search results"
    )
    active_alerts = models.PositiveIntegerField(default=0, help_text="Number of active alerts")
    sentiment_category = models.CharField(
        max_length=10, 
        choices=SENTIMENT_CHOICES, 
        default='neutral',
        help_text="Overall sentiment category of mentions (positive/neutral/negative)"
    )
    sentiment_score = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        help_text="Sentiment score (-1.00 to 1.00)"
    )
    # Processing/tracking fields (to align with engine shared_models)
    processing_status = models.CharField(
        max_length=10,
        choices=PROCESSING_STATUS_CHOICES,
        default='INIT',
        help_text="Current processing status of the domain"
    )
    misinformation_scan_status = models.CharField(
        max_length=15,
        choices=MISINFO_SCAN_STATUS_CHOICES,
        default='NOT_READY',
        help_text="Misinformation scanning status for this domain"
    )
    last_misinformation_scan_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last misinformation scan"
    )
    track_message = models.TextField(
        blank=True,
        null=True,
        help_text="Message or notes about the processing status"
    )
    tracked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the domain was last tracked"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the domain was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the domain was last modified")
    
    class Meta:
        db_table = 'domains'
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'
        ordering = ['name']
        unique_together = ['url', 'organisation']
        indexes = [
            models.Index(fields=['organisation', 'processing_status']),
            models.Index(fields=['organisation', '-visibility_score']),
            models.Index(fields=['processing_status', 'tracked_at']),
            models.Index(fields=['sentiment_category', '-sentiment_score']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"


# DomainAccess model removed - domain-level access management deprecated
class DomainAccess(models.Model):
    """
    Controls which users can access specific domains (no granular levels)
    """
    user = models.ForeignKey(
        'authentication.Account',
        on_delete=models.CASCADE,
        related_name='domain_access'
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='user_access'
    )
    granted_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.CASCADE,
        related_name='granted_domain_access'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'domain']
        db_table = 'domain_access'
        verbose_name = 'Domain Access'
        verbose_name_plural = 'Domain Access'
        indexes = [
            models.Index(fields=['granted_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.domain.name}"