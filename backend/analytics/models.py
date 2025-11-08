from django.db import models
from domains.models import Domain
from competitors.models import Competitor


class SentimentAnalytics(models.Model):
    """
    SentimentAnalytics model for aggregated sentiment data by theme (snapshot pattern)
    Can be daily, weekly, monthly, or quarterly based on user preference.
    """
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='sentiment_analytics')
    theme = models.CharField(max_length=255)  # e.g., "Product Quality", "Taste"
    platform = models.CharField(max_length=100, null=True, blank=True)
    snapshot_date = models.DateField(help_text="Date of the snapshot (can be daily, weekly, monthly, quarterly)")
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default='daily',
        help_text="Type of period this snapshot represents"
    )
    
    # Sentiment breakdown
    positive_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    neutral_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    negative_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    mention_count = models.IntegerField(default=0)
    
    # 5 Core Metrics (for consistency with other snapshots)
    mentions = models.PositiveIntegerField(default=0, help_text="Total mentions")
    citations = models.PositiveIntegerField(default=0, help_text="Total citations")
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sentiment_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    average_position = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sentiment_analytics'
        unique_together = ['domain', 'theme', 'platform', 'snapshot_date', 'period_type']
        indexes = [
            models.Index(fields=['domain', 'snapshot_date']),
            models.Index(fields=['theme', 'snapshot_date']),
            models.Index(fields=['domain', 'platform', 'snapshot_date']),
            models.Index(fields=['domain', 'theme', '-sentiment_score']),
            models.Index(fields=['snapshot_date', '-mention_count']),
            models.Index(fields=['domain', 'period_type', 'snapshot_date']),
        ]
        ordering = ['-snapshot_date']
    
    def save(self, *args, **kwargs):
        """
        Override save to prevent empty string or NULL platforms from being saved.
        Platform must be a valid platform name (e.g., 'ChatGPT', 'Google Gemini', 'Perplexity').
        Empty strings and NULL are not allowed and will raise a ValueError.
        """
        # CRITICAL: Never save empty string or NULL for platform - only save valid platform names
        # If platform is empty string or None, raise an error to prevent invalid data
        if self.platform == '' or self.platform is None:
            raise ValueError(
                f"Cannot save SentimentAnalytics with empty or NULL platform. "
                f"Platform must be a valid platform name (e.g., 'ChatGPT', 'Google Gemini', 'Perplexity'). "
                f"Domain: {self.domain}, Theme: {self.theme}"
            )
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.domain.name} - {self.theme} - {self.snapshot_date} ({self.period_type})"


class ShareOfVoiceAnalytics(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='sov_analytics')
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, null=True, blank=True, related_name='sov_analytics')
    # NULL competitor means this row is for your own brand
    platform = models.CharField(max_length=100, null=True, blank=True)  # NULL = overall
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    mention_count = models.IntegerField(default=0)
    market_position = models.IntegerField(null=True, blank=True)  # Rank (1 = leader, 2 = second, etc.)
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'share_of_voice_analytics'
        unique_together = [['domain', 'competitor', 'platform', 'timestamp']]
        indexes = [
            models.Index(fields=['domain', 'timestamp']),
            models.Index(fields=['competitor', 'timestamp']),
            # Additional indexes
            models.Index(fields=['domain', 'platform', 'timestamp']),
            models.Index(fields=['timestamp', '-share_percentage']),
            models.Index(fields=['domain', 'competitor', 'platform', 'timestamp']),
            models.Index(fields=['market_position', 'timestamp']),
        ]
        ordering = ['-timestamp', 'market_position']
    
    def __str__(self):
        competitor_name = self.competitor.name if self.competitor else self.domain.name
        platform_str = f" - {self.platform}" if self.platform else ""
        return f"{competitor_name}{platform_str} - {self.share_percentage}% - {self.timestamp}"

