from django.db import models
from domains.models import Domain
from authentication.models import Account


class Competitor(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='competitors')
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    total_mentions = models.IntegerField(default=0)
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    average_position = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    share_of_voice_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    trend_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='competitors_created')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'competitors'
        unique_together = [['name', 'domain']]
        indexes = [
            models.Index(fields=['domain']),
            # Additional indexes
            models.Index(fields=['domain', '-share_of_voice_percentage']),
            models.Index(fields=['domain', '-visibility_score']),
            models.Index(fields=['domain', '-total_mentions']),
            models.Index(fields=['domain', 'created_at']),
        ]
        ordering = ['-total_mentions']
    
    def __str__(self):
        return f"{self.name} (tracked by {self.domain.name})"


class CompetitorAnalytics(models.Model):
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='competitor_analytics')
    platform = models.CharField(max_length=100)
    total_mentions = models.IntegerField(default=0)
    position = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'competitor_analytics'
        indexes = [
            models.Index(fields=['competitor', 'timestamp']),
            models.Index(fields=['platform', 'timestamp']),
            # Additional indexes
            models.Index(fields=['competitor', 'platform', '-timestamp']),
            models.Index(fields=['timestamp', '-total_mentions']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.platform} - {self.timestamp}"


class CompetitorPrompt(models.Model):
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='competitor_prompts')
    prompt_text = models.TextField()
    total_mentions = models.IntegerField(default=0)
    position = models.IntegerField(default=0)
    your_mentions = models.IntegerField(default=0)
    platform_list = models.JSONField(default=list, blank=True)  # Array of platform names
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'competitor_prompts'
        indexes = [
            models.Index(fields=['competitor', '-total_mentions']),
            # Additional indexes
            models.Index(fields=['competitor', '-position']),
            models.Index(fields=['your_mentions', '-total_mentions']),  # CRITICAL: Gap analysis
            models.Index(fields=['competitor', 'created_at']),
        ]
        ordering = ['-total_mentions']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.prompt_text[:50]}..."

