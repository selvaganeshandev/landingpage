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
        unique_together = ['url', 'organisation']
        indexes = [
            models.Index(fields=['organisation', 'processing_status']),
            models.Index(fields=['organisation', '-visibility_score']),
            models.Index(fields=['processing_status', 'tracked_at']),
            models.Index(fields=['sentiment_category', '-sentiment_score']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"


# DomainAccess model removed - domain-level access management deprecated
class DomainAccess(models.Model):
    """
    Controls which users can access specific domains (no granular levels)
    """
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