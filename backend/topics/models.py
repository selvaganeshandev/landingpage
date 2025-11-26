from django.db import models
from domains.models import Domain
from authentication.models import Account
from keywords.models import Keyword


class Topic(models.Model):
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=255)
    keyword_list = models.JSONField(default=list, blank=True)  # Array of keyword strings
    total_mentions = models.IntegerField(default=0)
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    trend_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    platform_list = models.JSONField(default=list, blank=True)  # Array of platform names
    track_status = models.CharField(
        max_length=10,
        choices=TRACK_STATUS_CHOICES,
        default='INIT',
        help_text="Processing status: INIT/SCHD/PROC/COMP/FAIL"
    )
    track_message = models.TextField(
        blank=True, 
        null=True,
        help_text="Status message for tracking"
    )
    tracked_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Timestamp when tracking status was last updated"
    )
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='topics_created')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'topics'
        indexes = [
            models.Index(fields=['domain', '-total_mentions']),
            # Additional indexes
            models.Index(fields=['domain', '-visibility_score']),
            models.Index(fields=['domain', '-trend_percentage']),
            models.Index(fields=['domain', 'created_at']),
            models.Index(fields=['domain', 'track_status']),
        ]
        ordering = ['-total_mentions']
    
    def __str__(self):
        return f"{self.name} - {self.domain.name}"


class TopicAnalytics(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='topic_analytics')
    platform = models.CharField(
        max_length=100,
        default='All Platforms',
        help_text="AI platform name (e.g., ChatGPT, Claude, Perplexity). Use 'All Platforms' for aggregated data."
    )
    total_mentions = models.IntegerField(default=0)
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'topic_analytics'
        unique_together = ['topic', 'platform', 'timestamp']
        indexes = [
            models.Index(fields=['topic', 'platform', 'timestamp']),
            # Additional indexes
            models.Index(fields=['topic', '-timestamp', '-total_mentions']),
            models.Index(fields=['platform', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.topic.name} - {self.platform} - {self.timestamp}"


class TopicKeyword(models.Model):
    """
    Linking table between Topics and Keywords
    """
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('COMP', 'Completed'),
    ]
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='topic_keywords')
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='topic_keywords')
    relevance_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Relevance score of keyword to topic (0-100)"
    )
    track_status = models.CharField(
        max_length=10,
        choices=TRACK_STATUS_CHOICES,
        default='INIT',
        help_text="Processing status: INIT/COMP"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'topic_keywords'
        verbose_name = 'Topic Keyword'
        verbose_name_plural = 'Topic Keywords'
        unique_together = ['topic', 'keyword']
        indexes = [
            models.Index(fields=['topic', 'track_status']),
            models.Index(fields=['keyword', 'track_status']),
            models.Index(fields=['topic', '-relevance_score']),
        ]
    
    def __str__(self):
        return f"{self.topic.name} - {self.keyword.keyword}"


class PromptKeyword(models.Model):
    """
    Linking table between Prompts and Keywords
    Used to track which prompts are associated with which keywords
    """
    prompt = models.ForeignKey('prompts.Prompt', on_delete=models.CASCADE, related_name='prompt_keywords')
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='prompt_keywords')
    relevance_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Relevance score of prompt to keyword (0-100)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_keywords'
        verbose_name = 'Prompt Keyword'
        verbose_name_plural = 'Prompt Keywords'
        unique_together = ['prompt', 'keyword']
        indexes = [
            models.Index(fields=['prompt', 'keyword']),
            models.Index(fields=['keyword', 'prompt']),
            models.Index(fields=['keyword', '-relevance_score']),
        ]
    
    def __str__(self):
        return f"{self.prompt.prompt[:50]}... - {self.keyword.keyword}"


class KeywordAnalytics(models.Model):
    """
    Platform-wise analytics for keywords
    """
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]
    
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='keyword_analytics')
    platform = models.CharField(
        max_length=100, 
        help_text="AI platform name (e.g., ChatGPT, Claude, Perplexity)"
    )
    mentions = models.IntegerField(
        default=0, 
        help_text="Number of mentions of this keyword"
    )
    avg_position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.0,
        help_text="Average position in search results"
    )
    visibility_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Visibility score calculated from average position"
    )
    sentiment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Average sentiment score (-1.00 to 1.00)"
    )
    timestamp = models.DateField(
        help_text="Date of this analytics snapshot"
    )
    track_status = models.CharField(
        max_length=10,
        choices=TRACK_STATUS_CHOICES,
        default='INIT',
        help_text="Processing status: INIT/SCHD/PROC/COMP/FAIL"
    )
    track_message = models.TextField(
        blank=True, 
        null=True,
        help_text="Status message for tracking"
    )
    tracked_at = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Timestamp when tracking status was last updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'keyword_analytics'
        verbose_name = 'Keyword Analytics'
        verbose_name_plural = 'Keyword Analytics'
        unique_together = ['keyword', 'platform', 'timestamp']
        indexes = [
            models.Index(fields=['keyword', 'platform', 'timestamp']),
            models.Index(fields=['keyword', 'track_status']),
            models.Index(fields=['platform', 'timestamp']),
            models.Index(fields=['timestamp', '-mentions']),
        ]
        ordering = ['-timestamp', '-mentions']
    
    def __str__(self):
        return f"{self.keyword.keyword} - {self.platform} - {self.timestamp}"

