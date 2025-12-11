from django.db import models
from django.utils import timezone


class ReportTemplate(models.Model):
    """Predefined and custom report templates"""
    TEMPLATE_TYPE_CHOICES = [
        ('predefined', 'Predefined Template'),
        ('custom', 'Custom Template')
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        default='predefined',
        help_text='Type of report template'
    )

    # For predefined templates (legacy)
    sections = models.JSONField(
        default=list,
        blank=True,
        help_text='List of section names (used by predefined templates)'
    )

    # For custom templates (report builder)
    grid_rows = models.JSONField(
        default=list,
        blank=True,
        help_text='Grid layout configuration with widgets for custom reports'
    )

    # HTML template storage (for exact PDF rendering)
    html_template = models.TextField(
        blank=True,
        null=True,
        help_text='Rendered HTML template with placeholders for data injection'
    )
    css_template = models.TextField(
        blank=True,
        null=True,
        help_text='Compiled CSS styles (Tailwind) for the template'
    )

    # Organisation link (null for predefined, required for custom)
    organisation = models.ForeignKey(
        'authentication.Organisation',
        on_delete=models.CASCADE,
        related_name='custom_report_templates',
        null=True,
        blank=True,
        help_text='Organisation that owns this custom template (null for predefined templates)'
    )

    # Creator tracking
    created_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.SET_NULL,
        related_name='created_templates',
        null=True,
        blank=True,
        help_text='User who created this custom template'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_templates'
        ordering = ['name']
        indexes = [
            models.Index(fields=['organisation', 'template_type'], name='report_tmpl_org_type_idx'),
        ]

    def __str__(self):
        return self.name


class ScheduledReport(models.Model):
    """User-configured scheduled reports"""
    FREQUENCY_CHOICES = [
        ('once', 'One-time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused')
    ]

    organisation = models.ForeignKey(
        'authentication.Organisation',
        on_delete=models.CASCADE,
        related_name='scheduled_reports'
    )
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='scheduled_reports'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.PROTECT,
        related_name='scheduled_reports'
    )

    # Scheduling
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    schedule_day = models.IntegerField(null=True, blank=True)  # Day of week/month
    schedule_time = models.TimeField(default='09:00:00')

    # Configuration
    sections = models.JSONField(default=list)  # Selected sections
    formats = models.JSONField(default=list)  # ['PDF', 'Excel', 'Email']
    recipients = models.JSONField(default=list)  # Email addresses

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_generated_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.CASCADE,
        related_name='created_reports'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scheduled_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organisation', 'domain']),
            models.Index(fields=['status', 'next_run_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.frequency}"


class GeneratedReport(models.Model):
    """History of generated reports"""
    FORMAT_CHOICES = [
        ('PDF', 'PDF'),
        ('Excel', 'Excel'),
        ('PowerPoint', 'PowerPoint')
    ]

    scheduled_report = models.ForeignKey(
        ScheduledReport,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='generated_reports'
    )
    organisation = models.ForeignKey(
        'authentication.Organisation',
        on_delete=models.CASCADE,
        related_name='generated_reports'
    )
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='generated_reports'
    )

    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50)  # Template name

    # File information
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='PDF')
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)
    file_size = models.BigIntegerField(default=0)  # bytes
    page_count = models.IntegerField(default=0)

    # Metadata
    data_period_start = models.DateField()
    data_period_end = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports'
    )

    # Report content summary (JSON)
    summary_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'generated_reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['organisation', 'domain']),
            models.Index(fields=['generated_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.generated_at.strftime('%Y-%m-%d')}"
