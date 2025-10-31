from django.db import models
from domains.models import Domain
from competitors.models import Competitor


class SentimentAnalytics(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='sentiment_analytics')
    theme = models.CharField(max_length=255)  # e.g., "Product Quality", "Taste"
    positive_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    neutral_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    negative_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    mention_count = models.IntegerField(default=0)
    platform = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sentiment_analytics'
        indexes = [
            models.Index(fields=['domain', 'timestamp']),
            models.Index(fields=['theme', 'timestamp']),
            # Additional indexes
            models.Index(fields=['domain', 'platform', 'timestamp']),
            models.Index(fields=['domain', 'theme', '-negative_percentage']),
            models.Index(fields=['timestamp', '-mention_count']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.domain.name} - {self.theme} - {self.timestamp}"


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

