from django.db import models
from domains.models import Domain
from authentication.models import Account


class Integration(models.Model):
    INTEGRATION_TYPES = [
        ('google_analytics', 'Google Analytics'),
        ('search_console', 'Google Search Console'),
        ('slack', 'Slack'),
        ('sms', 'SMS Provider'),
        ('cms', 'CMS'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('error', 'Error'),
        ('disconnected', 'Disconnected'),
    ]
    
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='integrations')
    type = models.CharField(max_length=50, choices=INTEGRATION_TYPES)
    provider_id = models.CharField(max_length=255)  # GA property ID, GSC URL, etc.
    credentials = models.JSONField(default=dict)  # Encrypted OAuth tokens
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_sync_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='integrations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'integrations'
        unique_together = [['domain', 'type', 'provider_id']]
        indexes = [
            models.Index(fields=['domain', 'type']),
            models.Index(fields=['status', 'last_sync_at']),
            # Additional indexes
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['last_sync_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.domain.name} - {self.get_type_display()}"


class GATrafficInsight(models.Model):
    """Store Google Analytics traffic insights"""
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initialized'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]

    PERIOD_TYPE_CHOICES = [
        ('rolling_30d', 'Rolling 30 Days'),
        ('current_month', 'Current Month'),
        ('prev_month', 'Previous Month'),
        ('yoy_month', 'YoY Month'),
    ]

    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='ga_insights')
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='ga_traffic_insights')
    track_status = models.CharField(max_length=4, choices=TRACK_STATUS_CHOICES, default='INIT')
    track_message = models.TextField(null=True, blank=True)

    # Date range for this insight
    start_date = models.DateField()
    end_date = models.DateField()

    # Period classification for MoM/YoY (rolling_30d = legacy default)
    period_type = models.CharField(
        max_length=20, choices=PERIOD_TYPE_CHOICES, default='rolling_30d', db_index=True
    )
    
    # Overall metrics
    total_sessions = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)
    total_page_views = models.IntegerField(default=0)
    total_conversions = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bounce_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_session_duration = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # in seconds
    
    # AI platform traffic breakdown (stored as JSON)
    platform_breakdown = models.JSONField(default=dict)  # {platform: {visits, conversions, revenue, bounce_rate, avg_duration}}
    
    # Device breakdown
    device_breakdown = models.JSONField(default=dict)  # {device: {sessions, percentage, conversions, revenue}}
    
    # Geographic breakdown
    geographic_breakdown = models.JSONField(default=dict)  # {country: {sessions, percentage, revenue}}
    
    # Landing pages
    landing_pages = models.JSONField(default=list)  # [{page, sessions, bounce_rate, avg_duration, conversions}]
    
    # Conversion paths
    conversion_paths = models.JSONField(default=list)  # [{path, conversions, value, avg_time}]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'integrations'
        db_table = 'ga_traffic_insights'
        unique_together = [['integration', 'start_date', 'end_date']]
        indexes = [
            models.Index(fields=['domain', 'track_status']),
            models.Index(fields=['integration', 'start_date', 'end_date']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['track_status', 'created_at']),  # For scheduler to find INIT records
        ]
        ordering = ['-end_date', '-created_at']
    
    def __str__(self):
        return f"GA Insight for {self.domain.name} ({self.start_date} to {self.end_date})"


class GSCTrafficInsight(models.Model):
    """Store Google Search Console traffic insights"""
    TRACK_STATUS_CHOICES = [
        ('INIT', 'Initialized'),
        ('PROC', 'Processing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]

    PERIOD_TYPE_CHOICES = [
        ('rolling_30d', 'Rolling 30 Days'),
        ('current_month', 'Current Month'),
        ('prev_month', 'Previous Month'),
        ('yoy_month', 'YoY Month'),
    ]

    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='gsc_insights')
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name='gsc_traffic_insights')
    track_status = models.CharField(max_length=4, choices=TRACK_STATUS_CHOICES, default='INIT')
    track_message = models.TextField(null=True, blank=True)

    # Date range for this insight
    start_date = models.DateField()
    end_date = models.DateField()

    # Period classification for MoM/YoY (rolling_30d = legacy default)
    period_type = models.CharField(
        max_length=20, choices=PERIOD_TYPE_CHOICES, default='rolling_30d', db_index=True
    )
    
    # Overall metrics
    total_impressions = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    avg_ctr = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Click-through rate
    avg_position = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Top search queries
    top_queries = models.JSONField(default=list)  # [{query, impressions, clicks, ctr, position}]
    
    # Top pages
    top_pages = models.JSONField(default=list)  # [{page, impressions, clicks, ctr, position}]
    
    # Device breakdown
    device_breakdown = models.JSONField(default=dict)  # {device: {impressions, clicks, ctr}}
    
    # Country breakdown
    country_breakdown = models.JSONField(default=dict)  # {country: {impressions, clicks, ctr}}
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'integrations'
        db_table = 'gsc_traffic_insights'
        unique_together = [['integration', 'start_date', 'end_date']]
        indexes = [
            models.Index(fields=['domain', 'track_status']),
            models.Index(fields=['integration', 'start_date', 'end_date']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['track_status', 'created_at']),  # For scheduler to find INIT records
        ]
        ordering = ['-end_date', '-created_at']
    
    def __str__(self):
        return f"GSC Insight for {self.domain.name} ({self.start_date} to {self.end_date})"
