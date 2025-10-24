from django.db import models


class PromptCluster(models.Model):
    """
    PromptCluster model representing clusters of prompts for domains
    """
    cluster_id = models.CharField(max_length=100, unique=True, help_text="Unique identifier for the cluster")
    domain = models.ForeignKey(
        'domains.Domain', 
        on_delete=models.CASCADE, 
        related_name='prompt_clusters',
        help_text="Domain this cluster belongs to"
    )
    organisation = models.ForeignKey(
        'authentication.Organisation', 
        on_delete=models.CASCADE, 
        related_name='prompt_clusters',
        help_text="Organisation this cluster belongs to"
    )
    total_mentions = models.PositiveIntegerField(default=0, help_text="Total number of mentions")
    total_citations = models.PositiveIntegerField(default=0, help_text="Total number of citations")
    average_position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Average position in search results"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the cluster was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the cluster was last modified")
    
    class Meta:
        db_table = 'prompt_clusters'
        verbose_name = 'Prompt Cluster'
        verbose_name_plural = 'Prompt Clusters'
        ordering = ['cluster_id']
        unique_together = ['cluster_id', 'domain']
    
    def __str__(self):
        return f"Cluster {self.cluster_id} ({self.domain.name})"


class Prompt(models.Model):
    """
    Prompt model representing individual prompts within clusters
    """
    TRACK_STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ]
    
    TYPE_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
    ]
    
    prompt = models.TextField(help_text="The actual prompt text")
    cluster = models.ForeignKey(
        PromptCluster, 
        on_delete=models.CASCADE, 
        related_name='prompts',
        help_text="Cluster this prompt belongs to"
    )
    domain = models.ForeignKey(
        'domains.Domain', 
        on_delete=models.CASCADE, 
        related_name='prompts',
        help_text="Domain this prompt belongs to"
    )
    organisation = models.ForeignKey(
        'authentication.Organisation', 
        on_delete=models.CASCADE, 
        related_name='prompts',
        help_text="Organisation this prompt belongs to"
    )
    track_status = models.CharField(
        max_length=10, 
        choices=TRACK_STATUS_CHOICES, 
        default='active',
        help_text="Current tracking status of the prompt"
    )
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES, 
        default='primary',
        help_text="Type of prompt (primary or secondary)"
    )
    last_tracked_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Timestamp when the prompt was last tracked"
    )
    track_message = models.TextField(
        blank=True,
        help_text="Message or notes about the tracking status"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the prompt was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the prompt was last modified")
    
    class Meta:
        db_table = 'prompts'
        verbose_name = 'Prompt'
        verbose_name_plural = 'Prompts'
        ordering = ['prompt']
        unique_together = ['prompt', 'cluster']
    
    def __str__(self):
        return f"{self.prompt[:50]}... ({self.type})"


class PromptAnalytics(models.Model):
    """
    PromptAnalytics model representing analytics data for prompts
    """
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    prompt = models.ForeignKey(
        Prompt, 
        on_delete=models.CASCADE, 
        related_name='analytics',
        help_text="Prompt this analytics data belongs to"
    )
    domain = models.ForeignKey(
        'domains.Domain', 
        on_delete=models.CASCADE, 
        related_name='prompt_analytics',
        help_text="Domain this analytics belongs to"
    )
    organisation = models.ForeignKey(
        'authentication.Organisation', 
        on_delete=models.CASCADE, 
        related_name='prompt_analytics',
        help_text="Organisation this analytics belongs to"
    )
    platform = models.CharField(max_length=100, default='ChatGPT', help_text="Name of the AI platform used")
    is_mention = models.BooleanField(
        default=False,
        help_text="Whether this analytics entry is a mention or not"
    )
    total_mentions = models.PositiveIntegerField(default=0, help_text="Total number of mentions")
    total_citations = models.PositiveIntegerField(default=0, help_text="Total number of citations")
    position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Position in search results"
    )
    sentiment = models.CharField(
        max_length=10, 
        choices=SENTIMENT_CHOICES, 
        default='neutral',
        help_text="Sentiment of the analytics"
    )
    sentiment_score = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        help_text="Sentiment score (-1.00 to 1.00)"
    )
    context_summary = models.TextField(blank=True, help_text="Summary of the context")
    citations = models.JSONField(
        default=list,
        blank=True,
        help_text="List of citations with text and source URLs"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the analytics was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the analytics was last modified")
    
    class Meta:
        db_table = 'prompt_analytics'
        verbose_name = 'Prompt Analytics'
        verbose_name_plural = 'Prompt Analytics'
        ordering = ['-created_at']
        unique_together = ['prompt', 'platform']
    
    def __str__(self):
        return f"Analytics for {self.prompt.prompt[:30]}... ({self.platform})"