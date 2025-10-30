from django.db import models


class Domain(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
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
    sentiment = models.CharField(
        max_length=10, 
        choices=SENTIMENT_CHOICES, 
        default='neutral',
        help_text="Overall sentiment of mentions"
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
    track_status = models.CharField(
        max_length=50,
        default='INIT',
        help_text="Detailed tracking status"
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
    
    def __str__(self):
        return f"{self.name} ({self.url})"


class DetectedModel(models.Model):
    """
    Model for tracking detected AI models from mentions
    """
    MODEL_CHOICES = [
        ('ChatGPT', 'ChatGPT'),
        ('Google Gemini', 'Google Gemini'),
        ('Perplexity', 'Perplexity'),
        ('Claude', 'Claude'),
        ('Copilot', 'Copilot'),
        ('Other', 'Other'),
    ]
    
    name = models.CharField(
        max_length=50,
        choices=MODEL_CHOICES,
        help_text="Name of the detected AI model"
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='detected_models',
        help_text="Domain where this model was detected"
    )
    organisation = models.ForeignKey(
        'authentication.Organisation',
        on_delete=models.CASCADE,
        related_name='detected_models',
        help_text="Organisation this detection belongs to"
    )
    detection_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of times this model was detected"
    )
    first_detected = models.DateTimeField(
        auto_now_add=True,
        help_text="When this model was first detected"
    )
    last_detected = models.DateTimeField(
        auto_now=True,
        help_text="When this model was last detected"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this model detection is active"
    )
    
    class Meta:
        db_table = 'detected_models'
        verbose_name = 'Detected Model'
        verbose_name_plural = 'Detected Models'
        ordering = ['-last_detected']
        unique_together = ['name', 'domain']
    
    def __str__(self):
        return f"{self.name} - {self.domain.name}"


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

    def __str__(self):
        return f"{self.user.email} - {self.domain.name}"