from django.db import models


class Domain(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ('INIT', 'Initial'),
        ('SCHD', 'Scheduled'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]

    MISINFO_SCAN_STATUS_CHOICES = [
        ('NOT_READY', 'Not Ready'),      # No prompt analytics data yet
        ('READY', 'Ready'),               # Has data, ready to scan
        ('SCANNING', 'Scanning'),         # Scan in progress
        ('SCANNED', 'Scanned'),           # Scan completed
        ('NO_ISSUES', 'No Issues Found'), # Scan completed with no alerts
    ]

    COMPETITOR_ANALYSIS_STATUS_CHOICES = [
        ('NOT_READY', 'Not Ready'),      # No prompt analytics data yet
        ('READY', 'Ready'),               # Has data, ready to analyze
        ('ANALYZING', 'Analyzing'),       # Analysis in progress
        ('COMPLETED', 'Completed'),       # Analysis completed
    ]
    """
    Domain model representing websites or domains being monitored
    """
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    name = models.CharField(max_length=255, help_text="Name of the domain")
    url = models.URLField(help_text="URL of the domain")
    short_description = models.CharField(max_length=500, blank=True, null=True, help_text="Brief description of the brand/domain")

    # Content Guidelines fields
    tone_of_voice = models.TextField(blank=True, null=True, help_text="Brand's tone of voice guidelines")
    content_style = models.TextField(blank=True, null=True, help_text="Preferred content style guidelines")
    key_messages = models.TextField(blank=True, null=True, help_text="Key messages or themes to emphasize")
    topics_to_avoid = models.TextField(blank=True, null=True, help_text="Topics or themes to avoid in content")

    # Brand Identity fields
    target_audience = models.TextField(blank=True, null=True, help_text="Target audience demographics and preferences")
    brand_values = models.TextField(blank=True, null=True, help_text="Brand's core values")
    key_competitors = models.TextField(blank=True, null=True, help_text="Main competitors")

    country = models.CharField(max_length=100, default='United States', help_text="Country name for domain context")
    niches = models.JSONField(blank=True, null=True, help_text="List of industry niches/categories for the brand")

    # ----- Commercial profile -----
    # Collected by the prompt-generation wizard and stored here rather than on
    # the run, because these are facts about the brand, not about one job.
    # Competitor analysis and reporting can use them too. All nullable: two
    # thirds of existing domains predate them.
    business_model = models.CharField(
        max_length=64, blank=True, default='',
        help_text="B2C ecommerce, B2B SaaS, Local services, ... — selects the prompt intent taxonomy",
    )
    offering_categories = models.JSONField(
        blank=True, null=True, help_text="Product/service categories the brand sells",
    )
    regions_served = models.JSONField(
        blank=True, null=True, help_text="Cities/regions served — country alone is too coarse for local queries",
    )
    price_positioning = models.CharField(
        max_length=32, blank=True, default='', help_text="Budget | Mid-market | Premium | Mixed",
    )
    use_cases = models.JSONField(
        blank=True, null=True, help_text="Use cases and occasions that drive purchases",
    )
    buying_criteria = models.JSONField(
        blank=True, null=True, help_text="Decision factors, e.g. same-day delivery, price, compliance",
    )
    common_objections = models.JSONField(
        blank=True, null=True, help_text="Pre-purchase concerns — feeds trust prompts",
    )
    differentiators = models.JSONField(
        blank=True, null=True, help_text="Why customers choose this brand — feeds comparison prompts",
    )
    organisation = models.ForeignKey(
        'authentication.Organisation',
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
    # Processing/tracking fields (to align with engine shared_models)
    processing_status = models.CharField(
        max_length=10,
        choices=PROCESSING_STATUS_CHOICES,
        default='INIT',
        help_text="Current processing status of the domain"
    )
    misinformation_scan_status = models.CharField(
        max_length=15,
        choices=MISINFO_SCAN_STATUS_CHOICES,
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
        choices=COMPETITOR_ANALYSIS_STATUS_CHOICES,
        default='NOT_READY',
        help_text="Competitor analysis status for this domain"
    )
    last_competitor_analysis_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last competitor analysis"
    )
    # How often the full sweep re-runs this domain's prompts.
    #
    # The sweep is the one job that re-queries a whole corpus at once, and its
    # cost scales with it (~15,760 LLM calls a run on production). The corpus is
    # long-tailed — a handful of domains hold most of the prompts — so the tail
    # does not need the same cadence as the head. Before this field the tiers
    # came from a server env list (WEEKLY_SWEEP_WEEKLY_DOMAIN_IDS), which meant
    # a deploy to change one client's cadence; this makes it per-domain data a
    # client can set for themselves.
    #
    # 'weekly' is the default so behaviour is unchanged for every existing
    # domain: the untiered sweep already ran everything weekly.
    SWEEP_CADENCE_CHOICES = [
        ('weekly', 'Weekly'),
        ('biweekly', 'Every 15 days'),
        ('monthly', 'Every 30 days'),
        ('off', 'Off - no sweep'),
    ]
    sweep_cadence = models.CharField(
        max_length=10,
        choices=SWEEP_CADENCE_CHOICES,
        default='weekly',
        help_text="How often the full prompt sweep re-runs this domain",
    )

    # When the full sweep last re-queued this domain's prompts. Set by the sweep
    # itself, so a cadence longer than the weekly cron has something to measure
    # "is this domain due yet?" against. NULL means never swept since this field
    # existed, which counts as due — no domain is silently skipped on rollout.
    last_swept_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the full prompt sweep last covered this domain",
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
        db_table = 'domains'
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'
        ordering = ['-created_at']  # Most recently added first
        # No unique_together on (url, organisation): Rankmax tracks some sites
        # as two projects on one domain — Kotak811 and Shriram Wealth each have
        # a pair — and PromptMaxx has to be able to hold them the same way.
        #
        # Nothing else may create a duplicate by accident. The add-domain views
        # used to rely on the IntegrityError this constraint raised; they now
        # call domains.views.domain_already_tracked() before creating, which
        # compares on the bare host so www/scheme variants still collide.
        indexes = [
            models.Index(fields=['organisation', 'processing_status']),
            models.Index(fields=['organisation', '-visibility_score']),
            models.Index(fields=['processing_status', 'tracked_at']),
            models.Index(fields=['sentiment_category', '-sentiment_score']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"


# Default access level granted to a client on a domain.
DEFAULT_CLIENT_ACCESS_LEVEL = 'viewer'


class DomainAccess(models.Model):
    """
    Controls which users can access specific domains.

    ``access_level`` is reserved for future granular rights (unused in Phase 1 —
    every grant is a viewer). ``is_active`` is a soft-delete flag: revoking a
    client's access flips it to False rather than deleting the row, preserving
    assignment history and allowing instant restoration.
    """
    ACCESS_LEVEL_CHOICES = [
        ('viewer', 'Viewer'),
        ('analyst', 'Analyst'),
        ('manager', 'Manager'),
    ]

    user = models.ForeignKey(
        'authentication.Account',
        on_delete=models.CASCADE,
        related_name='domain_access'
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='user_access'
    )
    access_level = models.CharField(
        max_length=15,
        choices=ACCESS_LEVEL_CHOICES,
        default=DEFAULT_CLIENT_ACCESS_LEVEL,
        help_text="Granular access level (reserved; unused in Phase 1)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Soft-delete flag; False revokes access while preserving history"
    )
    granted_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.CASCADE,
        related_name='granted_domain_access'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'domain']
        db_table = 'domain_access'
        verbose_name = 'Domain Access'
        verbose_name_plural = 'Domain Access'
        indexes = [
            models.Index(fields=['granted_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.domain.name}"


class DomainHealthCheck(models.Model):
    """
    Stores historical health check results for domains
    Tracks AI-friendliness and SEO optimization over time
    """
    GRADE_CHOICES = [
        ('Excellent', 'Excellent'),
        ('Good', 'Good'),
        ('Fair', 'Fair'),
        ('Poor', 'Poor'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='health_checks',
        help_text="Domain this health check belongs to"
    )
    health_score = models.PositiveIntegerField(
        help_text="Total health score achieved (0-100)"
    )
    max_score = models.PositiveIntegerField(
        default=100,
        help_text="Maximum possible score"
    )
    percentage = models.PositiveIntegerField(
        help_text="Health score as percentage"
    )
    grade = models.CharField(
        max_length=10,
        choices=GRADE_CHOICES,
        help_text="Grade based on percentage (Excellent/Good/Fair/Poor)"
    )
    grade_color = models.CharField(
        max_length=10,
        help_text="Color for grade display (green/blue/yellow/red)"
    )

    # Store detailed check results as JSON
    checks = models.JSONField(
        help_text="Array of individual check results with status, score, message"
    )

    # Summary statistics
    total_checks = models.PositiveIntegerField(
        help_text="Total number of checks performed"
    )
    passed_checks = models.PositiveIntegerField(
        help_text="Number of checks that passed"
    )
    warning_checks = models.PositiveIntegerField(
        help_text="Number of checks with warnings"
    )
    failed_checks = models.PositiveIntegerField(
        help_text="Number of checks that failed"
    )

    # Metadata
    checked_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.SET_NULL,
        null=True,
        related_name='health_checks_performed',
        help_text="User who initiated the health check"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when health check was performed"
    )

    class Meta:
        db_table = 'domain_health_checks'
        verbose_name = 'Domain Health Check'
        verbose_name_plural = 'Domain Health Checks'
        ordering = ['-created_at']  # Most recent first
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['domain', '-health_score']),
            models.Index(fields=['grade', '-created_at']),
        ]

    def __str__(self):
        return f"{self.domain.name} - {self.percentage}% ({self.grade}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class InternalLinkMap(models.Model):
    """
    Stores internal link mapping for domains
    Used for inserting contextual links during content generation
    """
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='internal_links',
        help_text="Domain this link map belongs to"
    )
    topic = models.CharField(
        max_length=255,
        help_text="Topic or subject for the link"
    )
    keywords = models.TextField(
        help_text="Comma-separated keywords that should trigger this link"
    )
    url = models.URLField(
        max_length=500,
        help_text="URL to link to when keywords are matched"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the link map entry was created"
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the link map entry was last modified"
    )

    class Meta:
        db_table = 'internal_link_maps'
        verbose_name = 'Internal Link Map'
        verbose_name_plural = 'Internal Link Maps'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['domain', 'topic']),
        ]

    def __str__(self):
        return f"{self.domain.name} - {self.topic}"


class ReferenceDocument(models.Model):
    """
    Stores reference documents (PDF, PPT, Word, CSV, Excel) and text notes
    for a domain's Reference Repository. Extracted text is used during
    content generation to provide brand-specific context.
    """
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('pptx', 'PowerPoint'),
        ('docx', 'Word Document'),
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
        ('text', 'Text Note'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='reference_documents',
        help_text="Domain this reference document belongs to"
    )
    file = models.FileField(
        upload_to='reference_docs/%Y/%m/',
        blank=True,
        null=True,
        help_text="Uploaded file (null for text notes)"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Original file name or title for text notes"
    )
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        help_text="Type of reference document"
    )
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes (0 for text notes)"
    )
    extracted_text = models.TextField(
        blank=True,
        default='',
        help_text="Text content extracted from the uploaded file or user-entered text"
    )
    extraction_status = models.CharField(
        max_length=20,
        default='completed',
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        help_text="Status of text extraction from uploaded file"
    )
    extraction_error = models.TextField(
        blank=True,
        default='',
        help_text="Error message if text extraction failed"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="User-provided description or context about this document"
    )
    uploaded_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_reference_docs',
        help_text="User who uploaded this document"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the document was uploaded"
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the document was last modified"
    )

    # File size limits in bytes
    MAX_FILE_SIZES = {
        'pdf': 25 * 1024 * 1024,    # 25 MB
        'pptx': 25 * 1024 * 1024,   # 25 MB
        'docx': 25 * 1024 * 1024,   # 25 MB
        'csv': 25 * 1024 * 1024,    # 25 MB
        'xlsx': 25 * 1024 * 1024,   # 25 MB
    }
    MAX_TEXT_LENGTH = 50000  # 50,000 characters for text notes
    MAX_FILES_PER_DOMAIN = 20

    class Meta:
        db_table = 'reference_documents'
        verbose_name = 'Reference Document'
        verbose_name_plural = 'Reference Documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['domain', 'file_type']),
        ]

    def __str__(self):
        return f"{self.domain.name} - {self.file_name} ({self.file_type})"


class BrandLink(models.Model):
    """
    Stores brand digital asset links (social media, microsites, blogs, etc.)
    for a domain's Reference Repository. These URLs are crawled and their
    extracted content is used during content generation alongside reference documents.
    """
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter / X'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('microsite', 'Microsite'),
        ('blog', 'Blog'),
        ('other', 'Other'),
    ]

    EXTRACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='brand_links',
        help_text="Domain this brand link belongs to"
    )
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        help_text="Platform type for the link"
    )
    url = models.URLField(
        max_length=500,
        help_text="URL of the brand digital asset"
    )
    label = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Optional custom label for the link"
    )
    extracted_text = models.TextField(
        blank=True,
        default='',
        help_text="Text content extracted from crawling the URL"
    )
    extraction_status = models.CharField(
        max_length=20,
        choices=EXTRACTION_STATUS_CHOICES,
        default='pending',
        help_text="Status of text extraction from the URL"
    )
    extraction_error = models.TextField(
        blank=True,
        default='',
        help_text="Error message if text extraction failed"
    )
    added_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_brand_links',
        help_text="User who added this link"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the link was added"
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the link was last modified"
    )

    MAX_LINKS_PER_DOMAIN = 20

    class Meta:
        db_table = 'brand_links'
        verbose_name = 'Brand Link'
        verbose_name_plural = 'Brand Links'
        unique_together = ['domain', 'url']
        ordering = ['platform', '-created_at']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['domain', 'platform']),
        ]

    def __str__(self):
        return f"{self.domain.name} - {self.get_platform_display()} ({self.url})"


class BrandLinkChunk(models.Model):
    """
    Stores chunked text from BrandLink for efficient keyword-based
    matching during content generation — same approach as ReferenceDocumentChunk.
    """
    CHUNK_SIZE = 5000
    CHUNK_OVERLAP = 200

    brand_link = models.ForeignKey(
        'BrandLink',
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Parent brand link"
    )
    chunk_index = models.PositiveIntegerField(
        help_text="Order of this chunk within the brand link content (0-based)"
    )
    chunk_text = models.TextField(
        help_text="The text content of this chunk"
    )

    class Meta:
        db_table = 'brand_link_chunks'
        verbose_name = 'Brand Link Chunk'
        verbose_name_plural = 'Brand Link Chunks'
        ordering = ['brand_link', 'chunk_index']
        unique_together = ['brand_link', 'chunk_index']
        indexes = [
            models.Index(fields=['brand_link', 'chunk_index']),
        ]

    def __str__(self):
        return f"{self.brand_link.url} - Chunk {self.chunk_index}"


class ReferenceDocumentChunk(models.Model):
    """
    Stores chunked text from ReferenceDocument for efficient keyword-based
    matching during content generation. Instead of truncating large documents
    to 30K chars, we split the entire text into smaller chunks and only send
    keyword-relevant chunks to the AI.
    """
    CHUNK_SIZE = 5000  # characters per chunk
    CHUNK_OVERLAP = 200  # overlap between chunks for context continuity

    document = models.ForeignKey(
        ReferenceDocument,
        on_delete=models.CASCADE,
        related_name='chunks',
        help_text="Parent reference document"
    )
    chunk_index = models.PositiveIntegerField(
        help_text="Order of this chunk within the document (0-based)"
    )
    chunk_text = models.TextField(
        help_text="The text content of this chunk"
    )

    class Meta:
        db_table = 'reference_document_chunks'
        verbose_name = 'Reference Document Chunk'
        verbose_name_plural = 'Reference Document Chunks'
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
        ]

    def __str__(self):
        return f"{self.document.file_name} - Chunk {self.chunk_index}"


class DomainRegion(models.Model):
    """
    A geographic region a domain tracks AI visibility for (G1 of geographic
    AI-mention tracking — see docs/GEO_AI_MENTION_TRACKING_DESIGN.md).

    A domain with NO DomainRegion rows behaves exactly as before: the engine
    runs a single implicit 'GLOBAL' pass. Regions are opt-in per domain so the
    per-region query multiplier (prompts x platforms x regions) only applies
    where a brand actually wants multi-market tracking.
    """
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='regions',
        help_text="Domain this tracked region belongs to",
    )
    country_code = models.CharField(
        max_length=2,
        help_text="ISO 3166-1 alpha-2 country code, e.g. 'IN', 'US'",
    )
    country_name = models.CharField(
        max_length=100,
        help_text="Human-readable country name for display, e.g. 'India'",
    )
    locale = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional locale hint for prompt localization, e.g. 'en-IN'",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the engine should query this region on the next run",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary region for the domain (seeded from Domain.country)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'domain_regions'
        verbose_name = 'Domain Region'
        verbose_name_plural = 'Domain Regions'
        ordering = ['-is_primary', 'country_name']
        unique_together = ['domain', 'country_code']

    def __str__(self):
        return f"{self.domain.name} — {self.country_name} ({self.country_code})"