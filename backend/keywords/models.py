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
    last_used_for_generation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this keyword was last used to generate prompts"
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
        ]
    
    def __str__(self):
        return f"{self.keyword} ({self.domain.name})"