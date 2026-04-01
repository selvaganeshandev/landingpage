from django.db import models
from django.conf import settings
from django.utils import timezone
from domains.models import Domain


class GeneratedContent(models.Model):
    """
    GeneratedContent model for storing AI-generated articles and content
    """
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('topic', 'Topic Module'),
        ('content_gap', 'Content Gap Module'),
        ('answer_gap', 'Answer Gap Module'),
        ('manual', 'Manual Creation'),
    ]

    ARTICLE_TYPE_CHOICES = [
        # Article Types
        ('blog', 'Blog Post'),
        ('guide', 'How-to Guide'),
        ('comparison', 'Comparison Article'),
        ('listicle', 'Listicle'),
        ('technical', 'Technical Article'),
        # Web Page Content Types
        ('landing_page', 'Landing Page'),
        ('services_page', 'Services Page'),
        ('product_page', 'Product Page'),
        ('features_page', 'Features Page'),
        ('resource_page', 'Resource/Guide Page'),
        # Social Media Types
        ('twitter_post', 'Twitter/X Post'),
        ('linkedin_post', 'LinkedIn Post'),
        ('facebook_post', 'Facebook Post'),
        ('instagram_caption', 'Instagram Caption'),
        ('social_thread', 'Thread/Carousel'),
        # Community Post Types
        ('reddit_post', 'Reddit Post'),
        ('quora_answer', 'Quora Answer'),
        ('forum_post', 'Forum Post'),
        ('product_hunt', 'Product Hunt Launch'),
        ('newsletter_snippet', 'Newsletter Snippet'),
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

    # SEO meta fields (auto-generated)
    meta_title = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="SEO meta title (auto-generated, ~60 chars)"
    )
    meta_description = models.TextField(
        blank=True,
        default='',
        help_text="SEO meta description (auto-generated, ~160 chars)"
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
        max_length=30,
        choices=ARTICLE_TYPE_CHOICES,
        default='blog',
        help_text="Type of article"
    )
    keywords = models.TextField(help_text="Target keywords (comma-separated)")
    tone = models.TextField(
        default='professional',
        help_text="Tone of the content (professional, casual, friendly, authoritative)"
    )
    style = models.TextField(
        default='informative',
        help_text="Writing style (informative, persuasive, storytelling, analytical)"
    )
    goal = models.TextField(
        default='educate',
        help_text="Content goal (educate, convert, engage, inform)"
    )
    audience = models.TextField(
        default='general',
        help_text="Target audience (general, beginners, professionals, experts)"
    )
    depth = models.TextField(
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

    # AI Detection results
    ai_detection_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="AI-generated content probability score (0-100)"
    )
    human_detection_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Human-written content probability score (0-100)"
    )
    ai_detection_label = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="AI detection label (e.g., 'AI-generated', 'Human-written', 'Mixed')"
    )
    ai_detection_checked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time AI detection was run"
    )

    # Humanise feature fields
    HUMANISE_STATUS_CHOICES = [
        ('idle', 'Idle'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    humanise_status = models.CharField(
        max_length=20,
        choices=HUMANISE_STATUS_CHOICES,
        default='idle',
        help_text="Status of the humanisation process"
    )
    pre_humanise_content = models.TextField(
        null=True,
        blank=True,
        help_text="Original HTML content before humanisation (for undo)"
    )
    humanise_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the humanisation process started"
    )
    humanise_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the humanisation process completed"
    )
    humanise_error = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if humanisation failed"
    )

    # Refurbish tracking
    refurbished_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refurbished_versions',
        help_text="Original content this was refurbished from"
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


class CMSProvider(models.Model):
    """
    CMS Provider configuration for domains
    Supports multiple providers per domain (e.g., multiple WordPress sites)
    """
    PROVIDER_CHOICES = [
        ('wordpress', 'WordPress'),
        ('strapi', 'Strapi'),
        ('joomla', 'Joomla'),
        ('drupal', 'Drupal'),
        ('contentful', 'Contentful'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='cms_providers',
        help_text="Domain this CMS provider belongs to"
    )
    provider_type = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default='wordpress',
        help_text="Type of CMS provider"
    )
    name = models.CharField(
        max_length=200,
        help_text="Display name for this CMS provider (e.g., 'Main WordPress Site', 'Blog WordPress')"
    )
    
    # WordPress-specific settings (stored as JSON for flexibility)
    settings = models.JSONField(
        default=dict,
        help_text="Provider-specific settings"
    )
    # Example settings structure for WordPress:
    # {
    #     "api_url": "https://example.com/wp-json/wp/v2",
    #     "username": "admin",
    #     "app_password": "xxxx xxxx xxxx xxxx",  # Should be encrypted in production
    #     "site_url": "https://example.com",
    #     "content_type": "pages"  # or "posts"
    # }
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this CMS configuration is active"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Default CMS provider for this domain"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cms_providers'
        verbose_name = 'CMS Provider'
        verbose_name_plural = 'CMS Providers'
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['domain', 'provider_type']),
            models.Index(fields=['domain', 'is_active']),
        ]
        # Ensure only one default per domain
        constraints = [
            models.UniqueConstraint(
                fields=['domain'],
                condition=models.Q(is_default=True),
                name='unique_default_cms_per_domain'
            )
        ]
    
    def __str__(self):
        return f"{self.domain.name} - {self.name} ({self.provider_type})"


class ScheduledPublication(models.Model):
    """
    Scheduled publications for content
    Stores scheduled posts with their target CMS provider and schedule time
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('publishing', 'Publishing'),
        ('published', 'Published'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    content = models.ForeignKey(
        GeneratedContent,
        on_delete=models.CASCADE,
        related_name='scheduled_publications',
        help_text="Content to be published"
    )
    cms_provider = models.ForeignKey(
        CMSProvider,
        on_delete=models.CASCADE,
        related_name='scheduled_publications',
        help_text="CMS provider to publish to"
    )
    scheduled_at = models.DateTimeField(
        help_text="When to publish this content"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        help_text="Publication status"
    )
    
    # WordPress-specific metadata
    wordpress_post_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="WordPress post/page ID after publication"
    )
    wordpress_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL of published content"
    )
    
    # Error tracking
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if publication failed"
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual publication time"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scheduled_publications'
        verbose_name = 'Scheduled Publication'
        verbose_name_plural = 'Scheduled Publications'
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['cms_provider', 'scheduled_at']),
            models.Index(fields=['content', 'status']),
        ]
    
    def __str__(self):
        return f"{self.content.title} - {self.scheduled_at} ({self.status})"
    
    @property
    def is_overdue(self):
        """Check if scheduled time has passed but not yet published"""
        return (
            self.status == 'scheduled' and
            self.scheduled_at < timezone.now()
        )


class ContentComment(models.Model):
    """
    Google Docs-style comments on selected text within content.
    Reviewers select text and add comments/suggestions.
    Content owner can accept or reject each comment.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    content = models.ForeignKey(
        GeneratedContent,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="Content being commented on"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_comments',
        help_text="User who made the comment"
    )
    selected_text = models.TextField(
        help_text="The text that was highlighted/selected"
    )
    comment = models.TextField(
        help_text="The reviewer's comment or feedback"
    )
    suggestion = models.TextField(
        null=True,
        blank=True,
        help_text="Suggested replacement text (optional)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Comment status"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_comments',
        help_text="User who accepted/rejected the comment"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the comment was resolved"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'content_comments'
        verbose_name = 'Content Comment'
        verbose_name_plural = 'Content Comments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content', 'status']),
            models.Index(fields=['content', 'author']),
            models.Index(fields=['content', '-created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.author} on '{self.selected_text[:30]}...'"


class BulkUploadBatch(models.Model):
    """
    Represents a single bulk upload session.
    One user uploads one .xlsx file which becomes one batch.
    The queue engine processes items sequentially in a background thread.
    """
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('completed_with_errors', 'Completed with Errors'),
        ('failed', 'Failed'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='bulk_upload_batches',
        help_text="Domain this batch belongs to"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bulk_upload_batches',
        help_text="User who uploaded the file"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Original uploaded file name"
    )
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='processing',
        help_text="Overall batch status"
    )
    total_items = models.PositiveIntegerField(
        default=0,
        help_text="Total number of content items in batch"
    )
    processed_items = models.PositiveIntegerField(
        default=0,
        help_text="Number of items processed so far (generated + failed)"
    )
    successful_items = models.PositiveIntegerField(
        default=0,
        help_text="Number of items successfully generated"
    )
    failed_items = models.PositiveIntegerField(
        default=0,
        help_text="Number of items that failed generation"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Batch-level error message (e.g., parse failure)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the entire batch finished processing"
    )

    class Meta:
        db_table = 'bulk_upload_batches'
        verbose_name = 'Bulk Upload Batch'
        verbose_name_plural = 'Bulk Upload Batches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['uploaded_by', '-created_at']),
        ]

    def __str__(self):
        return f"Batch {self.id}: {self.file_name} ({self.status})"


class BulkUploadItem(models.Model):
    """
    Individual content item parsed from an uploaded .xlsx row.
    Tracks its generation lifecycle independently.
    Links to GeneratedContent once successfully generated.

    Status flow:
    - processed → generating → generated (automatic, queue engine)
    - generated → in_review → reviewed → approved (manual, user clicks)
    - generating → generation_failed (automatic, on error) → retry re-queues
    """
    STATUS_CHOICES = [
        ('processed', 'Processed'),
        ('generating', 'Generating'),
        ('generated', 'Generated'),
        ('generation_failed', 'Generation Failed'),
        ('in_review', 'In Review'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
    ]

    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    batch = models.ForeignKey(
        BulkUploadBatch,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Batch this item belongs to"
    )
    row_number = models.PositiveIntegerField(
        help_text="Row number in the Excel file (for reference)"
    )

    # Original Excel values (for display)
    content_category = models.CharField(
        max_length=50,
        help_text="Content category from Excel (Articles, Web Pages, Social Media, Community)"
    )
    content_type = models.CharField(
        max_length=50,
        help_text="Content type from Excel (Blog Post, Landing Page, etc.)"
    )

    # Mapped generation parameters
    title = models.CharField(max_length=500, help_text="Title from Excel")
    keywords = models.TextField(help_text="Keywords from Excel (comma-separated)")
    article_type = models.CharField(
        max_length=30,
        choices=GeneratedContent.ARTICLE_TYPE_CHOICES,
        default='blog',
        help_text="Mapped article type code for ClaudeContentGenerator"
    )
    target_country = models.CharField(max_length=100, default='united_states')
    target_language = models.CharField(max_length=100, default='us_english')
    target_audience = models.CharField(max_length=50, default='general')
    word_count = models.IntegerField(default=1500)
    tone = models.TextField(default='professional')
    style = models.TextField(default='informative')
    key_messages = models.TextField(blank=True, default='')
    topics_to_avoid = models.TextField(blank=True, default='')
    additional_instructions = models.TextField(blank=True, default='')
    reference_urls = models.TextField(blank=True, default='')
    reference_descriptions = models.TextField(blank=True, default='')
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processed',
        help_text="Item generation lifecycle status"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if generation failed"
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of retry attempts"
    )

    # Link to generated content (set after successful generation)
    generated_content = models.OneToOneField(
        GeneratedContent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_upload_item',
        help_text="The GeneratedContent record created from this item"
    )

    # Timestamps
    generation_started_at = models.DateTimeField(null=True, blank=True)
    generation_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bulk_upload_items'
        verbose_name = 'Bulk Upload Item'
        verbose_name_plural = 'Bulk Upload Items'
        ordering = ['row_number']
        indexes = [
            models.Index(fields=['batch', 'status']),
            models.Index(fields=['batch', 'row_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Item {self.row_number}: {self.title} ({self.status})"
