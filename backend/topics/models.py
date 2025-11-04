from django.db import models
from domains.models import Domain
from authentication.models import Account


class Topic(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=255)
    keyword_list = models.JSONField(default=list, blank=True)  # Array of keyword strings
    total_mentions = models.IntegerField(default=0)
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    trend_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    platform_list = models.JSONField(default=list, blank=True)  # Array of platform names
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
        ]
        ordering = ['-total_mentions']
    
    def __str__(self):
        return f"{self.name} - {self.domain.name}"


class TopicAnalytics(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='topic_analytics')
    total_mentions = models.IntegerField(default=0)
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'topic_analytics'
        indexes = [
            models.Index(fields=['topic', 'timestamp']),
            # Additional indexes
            models.Index(fields=['topic', '-timestamp', '-total_mentions']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.topic.name} - {self.timestamp}"


class TopicPrompt(models.Model):
    SEARCH_VOLUME_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='topic_prompts')
    prompt_text = models.TextField()
    relevance_score = models.IntegerField(default=0)  # 0-100
    search_volume = models.CharField(max_length=20, choices=SEARCH_VOLUME_CHOICES, default='medium')
    platform_list = models.JSONField(default=list, blank=True)  # Array of platform names
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'topic_prompts'
        indexes = [
            models.Index(fields=['topic', '-relevance_score']),
            # Additional indexes
            models.Index(fields=['search_volume', '-relevance_score']),
            models.Index(fields=['topic', 'search_volume']),
        ]
        ordering = ['-relevance_score']
    
    def __str__(self):
        return f"{self.topic.name} - {self.prompt_text[:50]}..."

