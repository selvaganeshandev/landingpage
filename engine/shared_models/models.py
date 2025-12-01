from django.db import models
from django.contrib.auth.models import AbstractUser


class Organisation(models.Model):
    """
    Organisation model representing companies or organizations
    """
    name = models.CharField(max_length=255, help_text="Name of the organisation")
    team_count = models.PositiveIntegerField(default=1, help_text="Number of team members")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the organisation was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the organisation was last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'organisations'
        managed = False  # Let backend manage this table
        verbose_name = 'Organisation'
        verbose_name_plural = 'Organisations'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Account(AbstractUser):
    """
    Read-only Account model for engine (matches backend schema).
    DO NOT use for authentication in engine - this is READ ONLY!
    Inherits from AbstractUser to match backend implementation.
    """
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrator'),
        ('admin', 'Administrator'),
        ('user', 'User'),
    ]
    
    # Custom fields (same as backend)
    email = models.EmailField(unique=True, help_text="Email address")
    role = models.CharField(
        max_length=12,
        choices=ROLE_CHOICES,
        default='user',
        help_text="Role of the account"
    )
    organisation = models.ForeignKey(
        Organisation, 
        on_delete=models.CASCADE, 
        related_name='accounts',
        help_text="Organisation this account belongs to"
    )
    active_domain_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of the currently active domain for this user"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the account was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the account was last modified")
    
    # Override groups and user_permissions to avoid clashes with auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="account_set",  # Custom related_name to avoid clash
        related_query_name="account",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="account_set",  # Custom related_name to avoid clash
        related_query_name="account",
    )
    
    # Authentication settings (same as backend)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'accounts'
        managed = False  # Let backend manage this table
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        ordering = ['email']
    
    def __str__(self):
        return f"{self.email} ({self.role})"


class Domain(models.Model):
    """
    Domain model representing websites or domains being monitored
    """
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    PROCESSING_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]
    
    name = models.CharField(max_length=255, help_text="Name of the domain")
    url = models.URLField(help_text="URL of the domain")
    country = models.CharField(max_length=100, default='United States', help_text="Country name for domain context")
    organisation = models.ForeignKey(
        Organisation, 
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
    # Processing status fields
    processing_status = models.CharField(
        max_length=10,
        choices=PROCESSING_STATUS_CHOICES,
        default='INIT',
        help_text="Current processing status of the domain"
    )
    misinformation_scan_status = models.CharField(
        max_length=15,
        default='NOT_READY',
        help_text="Misinformation scanning status for this domain"
    )
    last_misinformation_scan_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last misinformation scan"
    )
    competitor_analysis_status = models.CharField(
        max_length=15,
        default='NOT_READY',
        help_text="Competitor analysis status for this domain"
    )
    last_competitor_analysis_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last competitor analysis"
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
        app_label = 'shared_models'
        db_table = 'domains'
        managed = False  # Let backend manage this table
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'
        ordering = ['name']
        unique_together = ['url', 'organisation']
    
    def __str__(self):
        return f"{self.name} ({self.url})"


class Keyword(models.Model):
    """
    Keyword model representing keywords being tracked for domains
    """
    keyword = models.CharField(max_length=255, help_text="Keyword being tracked")
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        related_name='keywords',
        help_text="Domain this keyword belongs to"
    )
    auto_generate_prompts = models.BooleanField(
        default=True,
        help_text="If True, this keyword will be used to auto-generate prompt groups"
    )
    priority = models.IntegerField(
        default=0,
        help_text="Priority for prompt generation (higher = more important)"
    )
    last_used_for_generation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this keyword was last used to generate prompts"
    )
    last_used_for_topic_generation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this keyword was last used for topic generation (can be used multiple times)"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the keyword was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the keyword was last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'keywords'
        managed = False  # Let backend manage this table
        verbose_name = 'Keyword'
        verbose_name_plural = 'Keywords'
        ordering = ['keyword']
        unique_together = ['keyword', 'domain']
    
    def __str__(self):
        return f"{self.keyword} ({self.domain.name})"


class PromptGroup(models.Model):
    """
    PromptGroup model representing groups of prompts for domains
    """
    group_id = models.CharField(max_length=100, help_text="Unique identifier for the group")
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        related_name='prompt_groups',
        help_text="Domain this group belongs to"
    )
    theme = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Common theme extracted from prompts in this group using NLP"
    )
    total_mentions = models.PositiveIntegerField(default=0, help_text="Total number of mentions")
    total_citations = models.PositiveIntegerField(default=0, help_text="Total number of citations")
    average_position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Average position in search results"
    )
    visibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Visibility score calculated from average position"
    )
    sentiment_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average sentiment score (-1.00 to 1.00)"
    )
    
    # Tracking fields (aligned with Domain)
    track_status = models.CharField(
        max_length=10,
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
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this group is published and visible to users"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the group was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the group was last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'prompt_groups'
        managed = False  # Let backend manage this table
        verbose_name = 'Prompt Group'
        verbose_name_plural = 'Prompt Groups'
        ordering = ['group_id']
        unique_together = ['group_id', 'domain']
    
    def __str__(self):
        return f"Group {self.group_id} ({self.domain.name})"


class Prompt(models.Model):
    """
    Prompt model representing individual prompts within groups
    """
    # Standardized processing status choices
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
    ]
    
    prompt = models.TextField(help_text="The actual prompt text")
    group = models.ForeignKey(
        PromptGroup, 
        on_delete=models.CASCADE, 
        related_name='prompts',
        help_text="Group this prompt belongs to"
    )
    track_status = models.CharField(
        max_length=10,
        choices=TRACK_STATUS_CHOICES,
        default='INIT',
        help_text="Processing tracking status of the prompt"
    )
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES, 
        default='primary',
        help_text="Type of prompt (primary or secondary)"
    )
    tracked_at = models.DateTimeField(
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
        app_label = 'shared_models'
        db_table = 'prompts'
        managed = False  # Let backend manage this table
        verbose_name = 'Prompt'
        verbose_name_plural = 'Prompts'
        ordering = ['prompt']
        unique_together = ['prompt', 'group']
    
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
    # domain/organisation removed; derive via prompt.group.domain
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
    sentiment_category = models.CharField(
        max_length=10, 
        choices=SENTIMENT_CHOICES, 
        default='neutral',
        help_text="Sentiment category (positive/neutral/negative)"
    )
    sentiment_score = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        help_text="Sentiment score (-1.00 to 1.00)"
    )
    context_summary = models.TextField(blank=True, help_text="Summary of the context")
    citation_list = models.JSONField(
        default=list,
        blank=True,
        help_text="List of citations with text and source URLs"
    )
    # Enhanced fields for better functionality
    views = models.PositiveIntegerField(default=0, help_text="Number of views")
    shares = models.PositiveIntegerField(default=0, help_text="Number of shares")
    engagement_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Engagement score"
    )
    competitor_mention_list = models.JSONField(
        default=list,
        blank=True,
        help_text="List of competitor mentions"
    )
    topic_list = models.JSONField(
        default=list,
        blank=True,
        help_text="List of key topics extracted"
    )
    position_history_list = models.JSONField(
        default=list,
        blank=True,
        help_text="Historical position data"
    )
    
    
    track_status = models.CharField(
        max_length=10,
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
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this analytics is published and visible to users"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the analytics was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the analytics was last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'prompt_analytics'
        managed = False  # Let backend manage this table
        verbose_name = 'Prompt Analytics'
        verbose_name_plural = 'Prompt Analytics'
        ordering = ['-created_at']
        unique_together = ['prompt', 'platform']
    
    def __str__(self):
        return f"Analytics for {self.prompt.prompt[:30]}... ({self.platform})"


class Competitor(models.Model):
    """
    Competitor model representing competitor brands being tracked
    STATUS FLOW: INIT → SCHD → PROC → COMP (or FAIL)
    """
    STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Complete'),
        ('FAIL', 'Failed'),
    ]
    
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        related_name='competitors',
        help_text="Domain tracking this competitor"
    )
    name = models.CharField(max_length=255, help_text="Name of the competitor")
    url = models.URLField(max_length=500, help_text="URL of the competitor's website")
    track_status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='INIT', help_text="Processing status")
    track_message = models.TextField(blank=True, null=True, help_text="Status message or error details")
    tracked_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when last tracked")
    total_mentions = models.IntegerField(default=0, help_text="Total number of mentions")
    total_citations = models.IntegerField(default=0, help_text="Total number of citations")
    visibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Visibility score"
    )
    sentiment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Average sentiment score"
    )
    average_position = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Average position in AI responses"
    )
    share_of_voice_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Share of voice percentage"
    )
    trend_percentage = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=0.0,
        help_text="Trend percentage change"
    )
    created_by = models.ForeignKey(
        Account, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='competitors_created',
        help_text="Account that created this competitor"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'competitors'
        managed = False  # Let backend manage this table
        unique_together = [['name', 'domain']]
        ordering = ['-total_mentions']
    
    def __str__(self):
        return f"{self.name} (tracked by {self.domain.name})"


class CompetitorAnalytics(models.Model):
    """
    CompetitorAnalytics model for tracking competitor performance over time
    """
    competitor = models.ForeignKey(
        Competitor, 
        on_delete=models.CASCADE, 
        related_name='competitor_analytics',
        help_text="Competitor this analytics belongs to"
    )
    platform = models.CharField(max_length=100, help_text="AI platform name")
    total_mentions = models.IntegerField(default=0, help_text="Number of mentions on this date")
    position = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Average position"
    )
    sentiment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Average sentiment score"
    )
    timestamp = models.DateField(help_text="Date of this analytics snapshot")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'competitor_analytics'
        managed = False  # Let backend manage this table
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.platform} - {self.timestamp}"


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
    
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        related_name='sentiment_analytics',
        help_text="Domain this sentiment analytics belongs to"
    )
    theme = models.CharField(
        max_length=255, 
        help_text="Theme or topic (e.g., 'Product Quality', 'Customer Service')"
    )
    platform = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text="AI platform (null = aggregated across all platforms)"
    )
    snapshot_date = models.DateField(help_text="Date of the snapshot (can be daily, weekly, monthly, quarterly)")
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default='daily',
        help_text="Type of period this snapshot represents"
    )
    
    # Sentiment breakdown
    positive_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Percentage of positive sentiment"
    )
    neutral_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Percentage of neutral sentiment"
    )
    negative_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Percentage of negative sentiment"
    )
    mention_count = models.IntegerField(default=0, help_text="Number of mentions for this theme")
    
    # 5 Core Metrics (for consistency with other snapshots)
    mentions = models.PositiveIntegerField(default=0, help_text="Total mentions")
    citations = models.PositiveIntegerField(default=0, help_text="Total citations")
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    sentiment_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    average_position = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'sentiment_analytics'
        managed = False  # Let backend manage this table
        unique_together = ['domain', 'theme', 'platform', 'snapshot_date', 'period_type']
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
    """
    ShareOfVoiceAnalytics model for market share tracking
    """
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        related_name='sov_analytics',
        help_text="Domain this share of voice analytics belongs to"
    )
    competitor = models.ForeignKey(
        Competitor, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='sov_analytics',
        help_text="Competitor (null = your own brand)"
    )
    platform = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text="AI platform (null = aggregated across all platforms)"
    )
    share_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Share of voice percentage"
    )
    mention_count = models.IntegerField(default=0, help_text="Number of mentions")
    market_position = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Market rank (1 = leader, 2 = second, etc.)"
    )
    timestamp = models.DateField(help_text="Date of this analytics snapshot")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'share_of_voice_analytics'
        managed = False  # Let backend manage this table
        unique_together = [['domain', 'competitor', 'platform', 'timestamp']]
        ordering = ['-timestamp', 'market_position']
    
    def __str__(self):
        competitor_name = self.competitor.name if self.competitor else self.domain.name
        platform_str = f" - {self.platform}" if self.platform else ""
        return f"{competitor_name}{platform_str} - {self.share_percentage}% - {self.timestamp}"


class CompetitorPromptAnalytics(models.Model):
    """
    Links Competitors to Prompts and tracks analytics for each combination.
    STATUS FLOW: INIT → SCHD → PROC → COMP (or FAIL)
    """
    STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Complete'),
        ('FAIL', 'Failed'),
    ]
    
    competitor = models.ForeignKey(
        Competitor, 
        on_delete=models.CASCADE, 
        related_name='prompt_analytics',
        help_text="Competitor being tracked"
    )
    prompt = models.ForeignKey(
        Prompt, 
        on_delete=models.CASCADE, 
        related_name='competitor_analytics',
        help_text="Prompt being tested"
    )
    
    # Tracking fields
    track_status = models.CharField(
        max_length=4, 
        choices=STATUS_CHOICES, 
        default='INIT',
        help_text="Processing status"
    )
    track_message = models.TextField(
        blank=True, 
        null=True, 
        help_text="Status message or error details"
    )
    tracked_at = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Timestamp when last tracked"
    )
    
    # Analytics data (populated after ChatGPT testing)
    is_mentioned = models.BooleanField(
        default=False, 
        help_text="Whether competitor was mentioned"
    )
    position = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Position where competitor appears"
    )
    mention_count = models.IntegerField(
        default=0, 
        help_text="Number of times mentioned in response"
    )
    sentiment_category = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Sentiment category (positive/neutral/negative)"
    )
    sentiment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Sentiment score (-1 to 1)"
    )
    platform = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="AI platform (ChatGPT, Claude, etc.)"
    )
    response_text = models.TextField(
        blank=True, 
        null=True, 
        help_text="Full AI response"
    )
    citation_list = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Citations mentioning competitor"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'competitor_prompt_analytics'
        managed = False  # Let backend manage this table
        unique_together = [['competitor', 'prompt']]
        ordering = ['competitor', 'position']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.prompt.prompt[:50]}... [{self.track_status}]"


class CompetitorMetricSnapshot(models.Model):
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='shared_metric_snapshots', null=True, blank=True)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='shared_metric_snapshots')
    timestamp = models.DateTimeField(auto_now_add=True)
    total_mentions = models.IntegerField(default=0)
    total_citations = models.IntegerField(default=0)
    visibility_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    average_position = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    share_of_voice_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    trend_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    track_status = models.CharField(max_length=4, blank=True, null=True)
    platform_metrics = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'competitor_metric_snapshots'
        indexes = [
            models.Index(fields=['competitor', '-timestamp']),
            models.Index(fields=['domain', '-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        label = self.competitor.name if self.competitor else self.domain.name
        return f"{label} snapshot @ {self.timestamp}"


class CompetitiveInsight(models.Model):
    IMPACT_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='competitive_insights')
    title = models.CharField(max_length=255)
    description = models.TextField()
    insight_type = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, default='medium')
    snapshot_version = models.CharField(max_length=255)
    insight_data = models.JSONField(default=dict, blank=True)
    model_name = models.CharField(max_length=100, blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'competitive_insights'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['domain', '-generated_at']),
            models.Index(fields=['domain', 'snapshot_version']),
            models.Index(fields=['impact']),
        ]
        unique_together = [('domain', 'snapshot_version', 'title')]

    def __str__(self):
        return f"{self.domain.name} insight: {self.title}"


class PromptMetricSnapshot(models.Model):
    """
    Time-series snapshot of metrics for individual prompts.
    Can be daily, weekly, monthly, or quarterly based on user preference.
    """
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    prompt = models.ForeignKey(
        Prompt, 
        on_delete=models.CASCADE, 
        related_name='metric_snapshots',
        help_text="Prompt this snapshot belongs to"
    )
    platform = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        help_text="AI platform (null = aggregated across all platforms)"
    )
    snapshot_date = models.DateField(
        help_text="Date of the snapshot (can be daily, weekly, monthly, quarterly)"
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default='daily',
        help_text="Type of period this snapshot represents"
    )
    
    # 5 Core Metrics
    mentions = models.PositiveIntegerField(default=0, help_text="Total mentions")
    citations = models.PositiveIntegerField(default=0, help_text="Total citations")
    visibility_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Visibility score calculated from average position"
    )
    sentiment_score = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        help_text="Average sentiment score (-1.00 to 1.00)"
    )
    average_position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Average position in search results"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'prompt_metric_snapshots'
        managed = False  # Let backend manage this table
        unique_together = ['prompt', 'platform', 'snapshot_date', 'period_type']
        indexes = [
            models.Index(fields=['prompt', 'snapshot_date']),
            models.Index(fields=['platform', 'snapshot_date']),
            models.Index(fields=['snapshot_date', '-visibility_score']),
            models.Index(fields=['prompt', 'period_type', 'snapshot_date']),
        ]
        ordering = ['-snapshot_date']
    
    def __str__(self):
        platform_str = f" - {self.platform}" if self.platform else " (All Platforms)"
        return f"Prompt {self.prompt.id}{platform_str} - {self.snapshot_date} ({self.period_type})"


class PromptGroupMetricSnapshot(models.Model):
    """
    Time-series snapshot of aggregated metrics for prompt groups.
    Can be daily, weekly, monthly, or quarterly based on user preference.
    """
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    prompt_group = models.ForeignKey(
        PromptGroup, 
        on_delete=models.CASCADE, 
        related_name='metric_snapshots',
        help_text="Prompt group this snapshot belongs to"
    )
    platform = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        help_text="AI platform (null = aggregated across all platforms)"
    )
    snapshot_date = models.DateField(
        help_text="Date of the snapshot (can be daily, weekly, monthly, quarterly)"
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default='daily',
        help_text="Type of period this snapshot represents"
    )
    
    # 5 Core Metrics
    mentions = models.PositiveIntegerField(default=0, help_text="Total mentions")
    citations = models.PositiveIntegerField(default=0, help_text="Total citations")
    visibility_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Visibility score calculated from average position"
    )
    sentiment_score = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        help_text="Average sentiment score (-1.00 to 1.00)"
    )
    average_position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Average position in search results"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'prompt_group_metric_snapshots'
        managed = False  # Let backend manage this table
        unique_together = ['prompt_group', 'platform', 'snapshot_date', 'period_type']
        indexes = [
            models.Index(fields=['prompt_group', 'snapshot_date']),
            models.Index(fields=['platform', 'snapshot_date']),
            models.Index(fields=['snapshot_date', '-visibility_score']),
            models.Index(fields=['prompt_group', 'period_type', 'snapshot_date']),
        ]
        ordering = ['-snapshot_date']
    
    def __str__(self):
        platform_str = f" - {self.platform}" if self.platform else " (All Platforms)"
        return f"Group {self.prompt_group.group_id}{platform_str} - {self.snapshot_date} ({self.period_type})"


class DomainMetricSnapshot(models.Model):
    """
    Time-series snapshot of aggregated metrics for domains.
    Can be daily, weekly, monthly, or quarterly based on user preference.
    """
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        related_name='metric_snapshots',
        help_text="Domain this snapshot belongs to"
    )
    platform = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        help_text="AI platform (null = aggregated across all platforms)"
    )
    snapshot_date = models.DateField(
        help_text="Date of the snapshot (can be daily, weekly, monthly, quarterly)"
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default='daily',
        help_text="Type of period this snapshot represents"
    )
    
    # 5 Core Metrics
    mentions = models.PositiveIntegerField(default=0, help_text="Total mentions")
    citations = models.PositiveIntegerField(default=0, help_text="Total citations")
    visibility_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Visibility score calculated from average position"
    )
    sentiment_score = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        help_text="Average sentiment score (-1.00 to 1.00)"
    )
    average_position = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Average position in search results"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'domain_metric_snapshots'
        managed = False  # Let backend manage this table
        unique_together = ['domain', 'platform', 'snapshot_date', 'period_type']
        indexes = [
            models.Index(fields=['domain', 'snapshot_date']),
            models.Index(fields=['platform', 'snapshot_date']),
            models.Index(fields=['snapshot_date', '-visibility_score']),
            models.Index(fields=['domain', 'period_type', 'snapshot_date']),
        ]
        ordering = ['-snapshot_date']
    
    def __str__(self):
        platform_str = f" - {self.platform}" if self.platform else " (All Platforms)"
        return f"{self.domain.name}{platform_str} - {self.snapshot_date} ({self.period_type})"


class Topic(models.Model):
    """
    Topic model representing grouped keywords for domains
    STATUS FLOW: INIT → PROC → COMP (or FAIL)
    """
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]
    
    domain = models.ForeignKey(
        Domain, 
        on_delete=models.CASCADE, 
        related_name='topics',
        help_text="Domain this topic belongs to"
    )
    name = models.CharField(max_length=255, help_text="Name of the topic")
    keyword_list = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Array of keyword strings in this topic"
    )
    total_mentions = models.IntegerField(default=0, help_text="Total number of mentions")
    visibility_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Visibility score"
    )
    sentiment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Average sentiment score"
    )
    trend_percentage = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=0.0,
        help_text="Trend percentage change"
    )
    platform_list = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Array of platform names where topic appears"
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
    created_by = models.ForeignKey(
        Account, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='topics_created',
        help_text="Account that created this topic"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'topics'
        managed = False  # Let backend manage this table
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'
        ordering = ['-total_mentions']
        indexes = [
            models.Index(fields=['domain', '-total_mentions']),
            models.Index(fields=['domain', '-visibility_score']),
            models.Index(fields=['domain', '-trend_percentage']),
            models.Index(fields=['domain', 'created_at']),
            models.Index(fields=['domain', 'track_status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.domain.name}"


class TopicKeyword(models.Model):
    """
    Linking table between Topics and Keywords
    STATUS FLOW: INIT → COMP
    """
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('COMP', 'Completed'),
    ]
    
    topic = models.ForeignKey(
        Topic, 
        on_delete=models.CASCADE, 
        related_name='topic_keywords',
        help_text="Topic this keyword belongs to"
    )
    keyword = models.ForeignKey(
        Keyword, 
        on_delete=models.CASCADE, 
        related_name='topic_keywords',
        help_text="Keyword linked to this topic"
    )
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
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'topic_keywords'
        managed = False  # Let backend manage this table
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
    prompt = models.ForeignKey(
        Prompt, 
        on_delete=models.CASCADE, 
        related_name='prompt_keywords',
        help_text="Prompt linked to this keyword"
    )
    keyword = models.ForeignKey(
        Keyword, 
        on_delete=models.CASCADE, 
        related_name='prompt_keywords',
        help_text="Keyword linked to this prompt"
    )
    relevance_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Relevance score of prompt to keyword (0-100)"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'prompt_keywords'
        managed = False  # Let backend manage this table
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
    STATUS FLOW: INIT → PROC → COMP (or FAIL)
    """
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]
    
    keyword = models.ForeignKey(
        Keyword, 
        on_delete=models.CASCADE, 
        related_name='keyword_analytics',
        help_text="Keyword this analytics belongs to"
    )
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
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when last modified")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'keyword_analytics'
        managed = False  # Let backend manage this table
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


class TopicAnalytics(models.Model):
    """
    Time-series analytics for topics (platform-wise)
    """
    topic = models.ForeignKey(
        Topic, 
        on_delete=models.CASCADE, 
        related_name='topic_analytics',
        help_text="Topic this analytics belongs to"
    )
    platform = models.CharField(
        max_length=100,
        help_text="AI platform name (e.g., ChatGPT, Claude, Perplexity). Use 'All Platforms' for aggregated data."
    )
    total_mentions = models.IntegerField(default=0, help_text="Total number of mentions")
    visibility_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Visibility score"
    )
    sentiment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.0,
        help_text="Average sentiment score"
    )
    timestamp = models.DateField(help_text="Date of this analytics snapshot")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when created")
    
    class Meta:
        app_label = 'shared_models'
        db_table = 'topic_analytics'
        managed = False  # Let backend manage this table
        verbose_name = 'Topic Analytics'
        verbose_name_plural = 'Topic Analytics'
        unique_together = ['topic', 'platform', 'timestamp']
        indexes = [
            models.Index(fields=['topic', 'platform', 'timestamp']),
            models.Index(fields=['topic', '-timestamp', '-total_mentions']),
            models.Index(fields=['platform', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.topic.name} - {self.platform} - {self.timestamp}"


# Misinformation Models (read-only, managed by backend)
class MisinformationScan(models.Model):
    """
    Track scan runs per domain for misinformation detection.
    Read-only model for engine - table managed by backend.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='misinformation_scans',
        help_text="Domain being scanned"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the scan"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the scan started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the scan completed"
    )
    total_prompts_scanned = models.PositiveIntegerField(
        default=0,
        help_text="Number of prompts processed"
    )
    total_citations_found = models.PositiveIntegerField(
        default=0,
        help_text="Number of citation URLs found"
    )
    total_alerts_generated = models.PositiveIntegerField(
        default=0,
        help_text="Number of alerts created"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if scan failed"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'misinformation_scans'
        managed = False  # Let backend manage this table
        verbose_name = 'Misinformation Scan'
        verbose_name_plural = 'Misinformation Scans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Scan {self.id} - {self.domain.name} ({self.status})"


class CitationURL(models.Model):
    """
    Store all cited URLs from LLM responses.
    Read-only model for engine - table managed by backend.
    """
    CRAWL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='citation_urls',
        help_text="Associated domain"
    )
    prompt_analytics = models.ForeignKey(
        PromptAnalytics,
        on_delete=models.CASCADE,
        related_name='citation_urls',
        help_text="Source prompt result"
    )
    url = models.TextField(help_text="Full URL")
    url_hash = models.CharField(
        max_length=64,
        help_text="SHA256 hash for deduplication"
    )
    is_crawlable = models.BooleanField(
        default=True,
        help_text="Whether URL can be crawled"
    )
    crawl_status = models.CharField(
        max_length=20,
        choices=CRAWL_STATUS_CHOICES,
        default='pending',
        help_text="Current crawl status"
    )
    crawl_error = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if crawl failed"
    )
    http_status_code = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="HTTP response code"
    )
    last_crawled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful crawl time"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'citation_urls'
        managed = False  # Let backend manage this table
        verbose_name = 'Citation URL'
        verbose_name_plural = 'Citation URLs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'crawl_status']),
            models.Index(fields=['url_hash']),
            models.Index(fields=['domain', '-last_crawled_at']),
            models.Index(fields=['http_status_code']),
        ]

    def __str__(self):
        return f"{self.url[:50]}... ({self.crawl_status})"


class CitationContent(models.Model):
    """
    Cached content from crawled URLs.
    Read-only model for engine - table managed by backend.
    """
    citation_url = models.OneToOneField(
        CitationURL,
        on_delete=models.CASCADE,
        related_name='content',
        help_text="Associated citation URL"
    )
    raw_html = models.TextField(
        blank=True,
        null=True,
        help_text="Original HTML content"
    )
    extracted_text = models.TextField(
        blank=True,
        null=True,
        help_text="Clean extracted text"
    )
    page_title = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Page title"
    )
    meta_description = models.TextField(
        blank=True,
        null=True,
        help_text="Meta description"
    )
    publish_date = models.DateField(
        null=True,
        blank=True,
        help_text="Content publish date if found"
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA256 hash of extracted_text"
    )
    crawled_at = models.DateTimeField(
        auto_now=True,
        help_text="When content was fetched"
    )

    class Meta:
        app_label = 'shared_models'
        db_table = 'citation_content'
        managed = False  # Let backend manage this table
        verbose_name = 'Citation Content'
        verbose_name_plural = 'Citation Contents'

    def __str__(self):
        return f"Content for {self.citation_url.url[:50]}..."


class CitationMention(models.Model):
    """
    Tracks each occurrence of a citation URL in AI responses.
    Read-only model for engine - table managed by backend.
    """
    citation_url = models.ForeignKey(
        CitationURL,
        on_delete=models.CASCADE,
        related_name='mentions',
        help_text="The citation URL being mentioned"
    )
    prompt_analytics = models.ForeignKey(
        PromptAnalytics,
        on_delete=models.CASCADE,
        related_name='citation_mentions',
        help_text="The prompt analytics record containing this citation"
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='citation_mentions',
        help_text="Associated domain (denormalized for query efficiency)"
    )
    context_snippet = models.TextField(
        blank=True,
        null=True,
        help_text="Extracted context where this citation appeared in the response"
    )
    position_in_response = models.PositiveIntegerField(
        default=1,
        help_text="Position of this citation in the response (1st, 2nd, 3rd, etc.)"
    )
    is_primary_source = models.BooleanField(
        default=False,
        help_text="Whether this is the primary/main source cited for the claim"
    )
    mentioned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this citation was mentioned"
    )

    class Meta:
        app_label = 'shared_models'
        db_table = 'citation_mentions'
        managed = False  # Let backend manage this table
        verbose_name = 'Citation Mention'
        verbose_name_plural = 'Citation Mentions'
        ordering = ['-mentioned_at']
        indexes = [
            models.Index(fields=['domain', '-mentioned_at']),
            models.Index(fields=['citation_url', '-mentioned_at']),
            models.Index(fields=['prompt_analytics', 'position_in_response']),
            models.Index(fields=['domain', 'citation_url']),
        ]

    def __str__(self):
        return f"Mention of {self.citation_url.url[:30]}... at position {self.position_in_response}"


class MisinformationAlert(models.Model):
    """
    Detected misinformation issues and their status.
    Read-only model for engine - table managed by backend.
    """
    ALERT_TYPE_CHOICES = [
        ('misinformation', 'Misinformation'),
        ('broken_link', 'Broken Link'),
        ('outdated', 'Outdated Information'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='misinformation_alerts',
        help_text="Associated domain"
    )
    prompt = models.ForeignKey(
        Prompt,
        on_delete=models.CASCADE,
        related_name='misinformation_alerts',
        help_text="Source prompt"
    )
    prompt_analytics = models.ForeignKey(
        PromptAnalytics,
        on_delete=models.CASCADE,
        related_name='misinformation_alerts',
        help_text="Source prompt result"
    )
    citation_url = models.ForeignKey(
        CitationURL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
        help_text="Related citation URL (nullable for non-URL issues)"
    )
    scan = models.ForeignKey(
        MisinformationScan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
        help_text="Scan that generated this alert"
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPE_CHOICES,
        help_text="Type of alert"
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default='medium',
        help_text="Severity level"
    )
    llm_claim = models.TextField(help_text="What the LLM stated")
    source_content = models.TextField(
        blank=True,
        null=True,
        help_text="Relevant content from source"
    )
    explanation = models.TextField(
        blank=True,
        null=True,
        help_text="AI-generated explanation of the issue"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        help_text="Current status of the alert"
    )
    reviewed_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_misinformation_alerts',
        help_text="User who reviewed the alert"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the alert was reviewed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'misinformation_alerts'
        managed = False  # Let backend manage this table
        verbose_name = 'Misinformation Alert'
        verbose_name_plural = 'Misinformation Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'alert_type']),
            models.Index(fields=['domain', 'severity']),
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['alert_type', 'severity', 'status']),
            models.Index(fields=['prompt_analytics', 'alert_type']),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.domain.name}"


class MisinformationAnalytics(models.Model):
    """
    Daily aggregated metrics per domain for misinformation tracking.
    Read-only model for engine - table managed by backend.
    """
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='misinformation_analytics',
        help_text="Associated domain"
    )
    date = models.DateField(help_text="Analytics date")
    total_detected = models.PositiveIntegerField(
        default=0,
        help_text="Total alerts for the day"
    )
    broken_links_count = models.PositiveIntegerField(
        default=0,
        help_text="Broken link alerts"
    )
    misinformation_count = models.PositiveIntegerField(
        default=0,
        help_text="Misinformation alerts"
    )
    outdated_count = models.PositiveIntegerField(
        default=0,
        help_text="Outdated info alerts"
    )
    by_severity = models.JSONField(
        default=dict,
        help_text="Counts by severity: {low: x, medium: x, high: x, critical: x}"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'misinformation_analytics'
        managed = False  # Let backend manage this table
        verbose_name = 'Misinformation Analytics'
        verbose_name_plural = 'Misinformation Analytics'
        ordering = ['-date']
        unique_together = ['domain', 'date']
        indexes = [
            models.Index(fields=['domain', '-date']),
            models.Index(fields=['date', '-total_detected']),
        ]

    def __str__(self):
        return f"{self.domain.name} - {self.date}"