from django.db import models
from domains.models import Domain
from authentication.models import Account


class Competitor(models.Model):
    """
    STATUS FLOW: INIT → SCHD → PROC → COMP (or FAIL)
    - INIT: Competitor just created, ready to be processed
    - SCHD: Scheduled for processing (prompts being linked)
    - PROC: Processing competitor analytics
    - COMP: Completed processing
    - FAIL: Processing failed
    """
    STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Complete'),
        ('FAIL', 'Failed'),
    ]
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='competitors')
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    track_status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='INIT')
    track_message = models.TextField(blank=True, null=True)
    tracked_at = models.DateTimeField(null=True, blank=True)
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
            models.Index(fields=['track_status', 'modified_at']),
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
    """DEPRECATED: Use CompetitorPromptAnalytics instead"""
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


class CompetitorPromptAnalytics(models.Model):
    """
    Links Competitors to Prompts and tracks analytics for each combination.
    This replaces the old CompetitorPrompt model with a proper many-to-many relationship.
    
    STATUS FLOW: INIT → SCHD → PROC → COMP (or FAIL)
    """
    STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Complete'),
        ('FAIL', 'Failed'),
    ]
    
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='prompt_analytics')
    prompt = models.ForeignKey('prompts.Prompt', on_delete=models.CASCADE, related_name='competitor_analytics')
    
    # Tracking fields
    track_status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='INIT')
    track_message = models.TextField(blank=True, null=True)
    tracked_at = models.DateTimeField(null=True, blank=True)
    
    # Analytics data (populated after ChatGPT testing)
    is_mentioned = models.BooleanField(default=False)
    position = models.IntegerField(null=True, blank=True)  # Position where competitor appears
    mention_count = models.IntegerField(default=0)  # Number of times mentioned in response
    sentiment_category = models.CharField(max_length=50, blank=True, null=True)  # positive/neutral/negative
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    platform = models.CharField(max_length=100, blank=True, null=True)  # ChatGPT, Claude, etc.
    response_text = models.TextField(blank=True, null=True)  # Full AI response
    citation_list = models.JSONField(default=list, blank=True)  # Citations mentioning competitor
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'competitor_prompt_analytics'
        unique_together = [['competitor', 'prompt']]
        indexes = [
            models.Index(fields=['competitor', 'track_status']),
            models.Index(fields=['prompt', 'track_status']),
            models.Index(fields=['track_status', 'modified_at']),
            models.Index(fields=['competitor', 'is_mentioned']),
            models.Index(fields=['competitor', '-position']),
            models.Index(fields=['competitor', 'platform', 'tracked_at']),
        ]
        ordering = ['competitor', 'position']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.prompt.prompt_text[:50]}... [{self.track_status}]"

