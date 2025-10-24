from django.db import models


class Domain(models.Model):
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