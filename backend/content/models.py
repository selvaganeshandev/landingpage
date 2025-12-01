from django.db import models
from domains.models import Domain


class GeneratedContent(models.Model):
    """
    GeneratedContent model for storing AI-generated articles and content
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('published', 'Published'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('topic', 'Topic Module'),
        ('content_gap', 'Content Gap Module'),
        ('manual', 'Manual Creation'),
    ]

    ARTICLE_TYPE_CHOICES = [
        ('blog', 'Blog Post'),
        ('guide', 'How-to Guide'),
        ('comparison', 'Comparison Article'),
        ('listicle', 'Listicle'),
        ('technical', 'Technical Article'),
    ]

    # Core fields
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='generated_contents',
        help_text="Domain this content belongs to"
    )
    title = models.CharField(max_length=500, help_text="Title of the generated content")
    content_html = models.TextField(help_text="Generated content in HTML format")
    content_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Rich text editor JSON format (for TipTap/ProseMirror)"
    )

    # Source tracking
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        help_text="Source module that initiated content generation"
    )
    source_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of the source record (Topic ID or Content Gap ID)"
    )
    source_reference = models.TextField(
        null=True,
        blank=True,
        help_text="Additional source context (e.g., question text, topic name)"
    )

    # Generation parameters (for editing/regeneration)
    article_type = models.CharField(
        max_length=20,
        choices=ARTICLE_TYPE_CHOICES,
        default='blog',
        help_text="Type of article"
    )
    keywords = models.TextField(help_text="Target keywords (comma-separated)")
    tone = models.CharField(
        max_length=50,
        default='professional',
        help_text="Tone of the content (professional, casual, friendly, authoritative)"
    )
    style = models.CharField(
        max_length=50,
        default='informative',
        help_text="Writing style (informative, persuasive, storytelling, analytical)"
    )
    goal = models.CharField(
        max_length=50,
        default='educate',
        help_text="Content goal (educate, convert, engage, inform)"
    )
    audience = models.CharField(
        max_length=50,
        default='general',
        help_text="Target audience (general, beginners, professionals, experts)"
    )
    depth = models.CharField(
        max_length=50,
        default='comprehensive',
        help_text="Content depth (overview, detailed, comprehensive, extensive)"
    )
    word_count = models.IntegerField(
        default=1500,
        help_text="Target word count"
    )
    actual_word_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Actual word count of generated content"
    )

    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='generated',
        help_text="Status of the content"
    )
    scheduled_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled publication date"
    )
    published_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual publication date"
    )
    priority = models.CharField(
        max_length=10,
        default='medium',
        help_text="Priority level (high, medium, low)"
    )

    # AI generation metadata
    model_used = models.CharField(
        max_length=100,
        default='claude-3-5-sonnet-20241022',
        help_text="AI model used for generation"
    )
    generation_time_seconds = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Time taken to generate content"
    )
    prompt_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of prompt tokens used"
    )
    completion_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of completion tokens used"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'generated_contents'
        verbose_name = 'Generated Content'
        verbose_name_plural = 'Generated Contents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['source_type', 'source_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"


