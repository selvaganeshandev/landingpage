from django.db import models


class PromptGroup(models.Model):
    """
    PromptGroup model representing groups of prompts for domains
    """
    group_id = models.CharField(max_length=100, help_text="Unique identifier for the group")
    domain = models.ForeignKey(
        'domains.Domain', 
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
    # Tracking fields aligned with engine
    track_status = models.CharField(max_length=10, default='INIT', help_text="Processing status: INIT/SCHD/PROC/COMP/FAIL")
    track_message = models.TextField(blank=True, null=True, help_text="Status message for tracking")
    tracked_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when tracking status was last updated")
    is_published = models.BooleanField(default=False, help_text="Whether this group is published and visible to users")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the group was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the group was last modified")
    
    class Meta:
        db_table = 'prompt_groups'
        verbose_name = 'Prompt Group'
        verbose_name_plural = 'Prompt Groups'
        ordering = ['group_id']
        unique_together = ['group_id', 'domain']
        indexes = [
            models.Index(fields=['domain', 'is_published']),
            models.Index(fields=['domain', 'track_status']),
            models.Index(fields=['domain', '-total_mentions']),
        ]
    
    def __str__(self):
        return f"Group {self.group_id} ({self.domain.name})"


class Prompt(models.Model):
    """
    Prompt model representing individual prompts within groups
    """
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
        db_table = 'prompts'
        verbose_name = 'Prompt'
        verbose_name_plural = 'Prompts'
        ordering = ['prompt']
        unique_together = ['prompt', 'group']
        indexes = [
            models.Index(fields=['group', 'track_status']),
            models.Index(fields=['group', 'type']),
            models.Index(fields=['tracked_at']),
        ]
    
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
    platform = models.CharField(max_length=100, default='ChatGPT', help_text="Name of the AI platform used")
    region = models.CharField(
        max_length=8,
        default='GLOBAL',
        db_index=True,
        help_text="Geographic region: ISO 3166-1 alpha-2 country code, or 'GLOBAL' for unattributed. See docs/GEO_AI_MENTION_TRACKING_DESIGN.md.",
    )
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
    # Tracking fields
    track_status = models.CharField(max_length=10, default='INIT', help_text="Processing status: INIT/SCHD/PROC/COMP/FAIL")
    track_message = models.TextField(blank=True, null=True, help_text="Status message for tracking")
    tracked_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when tracking status was last updated")
    is_published = models.BooleanField(default=False, help_text="Whether this analytics is published and visible to users")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the analytics was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the analytics was last modified")
    
    class Meta:
        db_table = 'prompt_analytics'
        verbose_name = 'Prompt Analytics'
        verbose_name_plural = 'Prompt Analytics'
        ordering = ['-created_at']
        unique_together = ['prompt', 'platform', 'region']
        indexes = [
            models.Index(fields=['prompt', 'platform', 'created_at']),  # Time-series queries
            models.Index(fields=['prompt', 'is_mention', '-position']),  # Mention analysis
            models.Index(fields=['platform', 'is_mention', 'created_at']),  # Platform trends
            models.Index(fields=['prompt', '-sentiment_score']),  # Sentiment analysis
            models.Index(fields=['track_status', '-created_at']),  # Citations list filtering
        ]
    
    def __str__(self):
        return f"Analytics for {self.prompt.prompt[:30]}... ({self.platform})"


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
        db_table = 'prompt_metric_snapshots'
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
        db_table = 'prompt_group_metric_snapshots'
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
        'domains.Domain', 
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
    
    region = models.CharField(
        max_length=8,
        default='GLOBAL',
        db_index=True,
        help_text="Geographic region: ISO 3166-1 alpha-2 country code, or 'GLOBAL' for unattributed. See docs/GEO_AI_MENTION_TRACKING_DESIGN.md.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'domain_metric_snapshots'
        unique_together = ['domain', 'platform', 'snapshot_date', 'period_type', 'region']
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

class SweepGuardState(models.Model):
    """Cross-machine control state for the weekly full-corpus reprocess sweeps.

    A sweep resets EVERY prompt (or competitor) to INIT and re-queries every
    enabled platform — ~2,700 prompts x 4 platforms, roughly 10,800 paid LLM
    calls. The engine's cost guard used to keep its cooldown in a JSON file on
    the local filesystem, which made it per-machine: a sweep launched from a
    developer's laptop against this same database read that laptop's empty
    state, allowed itself, and stamped the cooldown somewhere the server could
    never see. That is exactly how five sweeps ran in the eleven days to
    2026-07-23 when only two were scheduled.

    Holding the state HERE — in the one database every caller must reach —
    makes the guard machine-independent: a sweep started anywhere is visible to
    every other caller.

    `enabled` is a hard kill switch. While it is False the sweep is refused
    unconditionally, including force=True, so no ad-hoc invocation can restart
    the spend. Re-enabling is a deliberate database edit, not a flag on a call.

    Owned by the backend; the engine declares a read/write mirror in
    shared_models and its migration is state-only.
    """

    sweep = models.CharField(
        max_length=32,
        unique=True,
        help_text="Sweep identifier: 'prompts' or 'competitors'",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Kill switch. When False this sweep is refused even with force=True.",
    )
    disabled_reason = models.TextField(
        blank=True,
        default='',
        help_text="Why the sweep was disabled, shown in the refusal payload",
    )
    last_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this sweep last began (stamped before any work is enqueued)",
    )
    runs = models.PositiveIntegerField(
        default=0,
        help_text="How many times this sweep has been admitted",
    )
    last_started_by = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="host/pid that last started the sweep, for attribution",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sweep_guard_state'
        verbose_name = 'Sweep Guard State'
        verbose_name_plural = 'Sweep Guard States'

    def __str__(self):
        return f"{self.sweep} (enabled={self.enabled}, runs={self.runs})"
