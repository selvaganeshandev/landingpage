from django.db import models
import hashlib


class MisinformationScan(models.Model):
    """
    Track scan runs per domain for misinformation detection.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    domain = models.ForeignKey(
        'domains.Domain',
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
        db_table = 'misinformation_scans'
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
    """
    CRAWL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('blocked', 'Blocked'),
    ]

    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='citation_urls',
        help_text="Associated domain"
    )
    prompt_analytics = models.ForeignKey(
        'prompts.PromptAnalytics',
        on_delete=models.CASCADE,
        related_name='citation_urls',
        help_text="Source prompt result"
    )
    url = models.TextField(
        help_text="Full URL"
    )
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
        db_table = 'citation_urls'
        verbose_name = 'Citation URL'
        verbose_name_plural = 'Citation URLs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'crawl_status']),
            models.Index(fields=['url_hash']),
            models.Index(fields=['domain', '-last_crawled_at']),
            models.Index(fields=['http_status_code']),
        ]

    def save(self, *args, **kwargs):
        # Generate URL hash if not set
        if not self.url_hash:
            self.url_hash = hashlib.sha256(self.url.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.url[:50]}... ({self.crawl_status})"


class CitationContent(models.Model):
    """
    Cached content from crawled URLs.
    Overwritten on updates, no history maintained.
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
        db_table = 'citation_content'
        verbose_name = 'Citation Content'
        verbose_name_plural = 'Citation Contents'

    def save(self, *args, **kwargs):
        # Generate content hash if extracted_text exists
        if self.extracted_text:
            self.content_hash = hashlib.sha256(self.extracted_text.encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Content for {self.citation_url.url[:50]}..."


class MisinformationAlert(models.Model):
    """
    Detected misinformation issues and their status.
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
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='misinformation_alerts',
        help_text="Associated domain"
    )
    prompt = models.ForeignKey(
        'prompts.Prompt',
        on_delete=models.CASCADE,
        related_name='misinformation_alerts',
        help_text="Source prompt"
    )
    prompt_analytics = models.ForeignKey(
        'prompts.PromptAnalytics',
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
    llm_claim = models.TextField(
        help_text="What the LLM stated"
    )
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
        'authentication.Account',
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
        db_table = 'misinformation_alerts'
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
    """
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='misinformation_analytics',
        help_text="Associated domain"
    )
    date = models.DateField(
        help_text="Analytics date"
    )
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
        db_table = 'misinformation_analytics'
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
