from django.db import models


class Keyword(models.Model):
    """
    Keyword model representing keywords being tracked for domains
    """
    keyword = models.CharField(max_length=255, help_text="Keyword being tracked")
    domain = models.ForeignKey(
        'domains.Domain',
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

    # Semantic keyword fields
    volume_level = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Search volume level: very-low, low, medium, high, very-high"
    )
    intent = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Search intent: informational, navigational, transactional, commercial"
    )
    entity = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Entity/subject of the keyword"
    )
    attribute = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Attribute/characteristic being queried"
    )
    variable = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Variable/modifier in the keyword"
    )
    source = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Source of keyword: ai-generated, seed, manual"
    )
    topic = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Main topic/category of the keyword"
    )
    cluster_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cluster identifier for grouping related keywords"
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
        db_table = 'keywords'
        verbose_name = 'Keyword'
        verbose_name_plural = 'Keywords'
        ordering = ['keyword']
        unique_together = ['keyword', 'domain']
        indexes = [
            models.Index(fields=['domain', 'created_at']),
            models.Index(fields=['domain', 'auto_generate_prompts', 'priority']),
            models.Index(fields=['domain', 'last_used_for_generation']),
            models.Index(fields=['domain', 'last_used_for_topic_generation']),
        ]
    
    def __str__(self):
        return f"{self.keyword} ({self.domain.name})"


class SecondaryKeyword(models.Model):
    """
    SecondaryKeyword model for storing AI-generated keywords that weren't selected as primary
    but can be used later for content generation or analysis
    """
    keyword = models.CharField(max_length=255, help_text="Keyword being stored")
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='secondary_keywords',
        help_text="Domain this keyword belongs to"
    )

    # Semantic keyword fields (same as Keyword model)
    volume_level = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Search volume level: very-low, low, medium, high, very-high"
    )
    intent = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Search intent: informational, navigational, transactional, commercial"
    )
    entity = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Entity/subject of the keyword"
    )
    attribute = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Attribute/characteristic being queried"
    )
    variable = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Variable/modifier in the keyword"
    )
    source = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Source of keyword: ai-generated, seed, manual"
    )
    topic = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Main topic/category of the keyword"
    )
    cluster_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cluster identifier for grouping related keywords"
    )

    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the keyword was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the keyword was last modified")

    class Meta:
        db_table = 'secondary_keywords'
        verbose_name = 'Secondary Keyword'
        verbose_name_plural = 'Secondary Keywords'
        ordering = ['keyword']
        unique_together = ['keyword', 'domain']
        indexes = [
            models.Index(fields=['domain', 'created_at']),
            models.Index(fields=['domain', 'topic']),
            models.Index(fields=['domain', 'cluster_id']),
        ]

    def __str__(self):
        return f"{self.keyword} ({self.domain.name})"