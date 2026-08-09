"""
Backlink profile shared models for the engine.
Unmanaged (managed=False) mirrors of the backend seo_rankings backlink tables.

Only the fields the fetch worker writes are mirrored — the backend owns the
schema (see backend/seo_rankings/models_backlinks.py) and the migrations.
"""
from django.db import models


class SeoBacklinkSnapshot(models.Model):
    """Mirror of backend seo_rankings.SeoBacklinkSnapshot"""
    STATUS_CHOICES = [
        ('PEND', 'Queued'),
        ('RUN', 'Fetching'),
        ('DONE', 'Complete'),
        ('FAIL', 'Failed'),
    ]

    domain_id = models.IntegerField()
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='PEND')
    requested_by_id = models.IntegerField(null=True, blank=True)

    rank = models.IntegerField(default=0)
    backlinks = models.BigIntegerField(default=0)
    backlinks_spam_score = models.IntegerField(default=0)
    broken_backlinks = models.BigIntegerField(default=0)
    broken_pages = models.BigIntegerField(default=0)
    crawled_pages = models.BigIntegerField(default=0)
    internal_links_count = models.BigIntegerField(default=0)
    external_links_count = models.BigIntegerField(default=0)

    referring_domains = models.IntegerField(default=0)
    referring_domains_nofollow = models.IntegerField(default=0)
    referring_main_domains = models.IntegerField(default=0)
    referring_main_domains_nofollow = models.IntegerField(default=0)
    referring_ips = models.IntegerField(default=0)
    referring_subnets = models.IntegerField(default=0)
    referring_pages = models.BigIntegerField(default=0)
    referring_pages_nofollow = models.BigIntegerField(default=0)

    first_seen = models.DateTimeField(null=True, blank=True)
    lost_date = models.DateTimeField(null=True, blank=True)

    referring_links_tld = models.JSONField(default=dict, blank=True)
    referring_links_types = models.JSONField(default=dict, blank=True)
    referring_links_attributes = models.JSONField(default=dict, blank=True)
    referring_links_platform_types = models.JSONField(default=dict, blank=True)
    referring_links_semantic_locations = models.JSONField(default=dict, blank=True)
    referring_links_countries = models.JSONField(default=dict, blank=True)
    target_info = models.JSONField(default=dict, blank=True)

    api_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    api_requests = models.IntegerField(default=0)
    is_truncated = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default='')

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    next_refresh_allowed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_backlink_snapshots'
        managed = False

    def __str__(self):
        return f"BacklinkSnapshot {self.id} domain={self.domain_id} [{self.status}]"


class SeoBacklinkItem(models.Model):
    """Mirror of backend seo_rankings.SeoBacklinkItem"""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot, on_delete=models.CASCADE,
        related_name='items', db_column='snapshot_id',
    )
    domain_from = models.CharField(max_length=255)
    url_from = models.TextField()
    url_to = models.TextField()
    tld_from = models.CharField(max_length=63, blank=True, default='')

    anchor = models.TextField(blank=True, default='')
    item_type = models.CharField(max_length=20, blank=True, default='')
    dofollow = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    is_broken = models.BooleanField(default=False)
    is_indirect_link = models.BooleanField(default=False)

    rank = models.IntegerField(default=0)
    page_from_rank = models.IntegerField(default=0)
    domain_from_rank = models.IntegerField(default=0)
    backlink_spam_score = models.IntegerField(default=0)

    page_from_title = models.TextField(blank=True, default='')
    page_from_language = models.CharField(max_length=16, blank=True, default='')
    page_from_external_links = models.IntegerField(default=0)
    page_from_internal_links = models.IntegerField(default=0)
    domain_from_country = models.CharField(max_length=8, blank=True, default='')
    domain_from_ip = models.CharField(max_length=45, blank=True, default='')
    domain_from_platform_type = models.JSONField(default=list, blank=True)
    semantic_location = models.CharField(max_length=64, blank=True, default='')
    attributes = models.JSONField(default=list, blank=True)

    url_to_status_code = models.IntegerField(null=True, blank=True)
    url_to_spam_score = models.IntegerField(default=0)

    first_seen = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    ranked_keywords_info = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_backlink_items'
        managed = False


class SeoBacklinkReferringDomain(models.Model):
    """Mirror of backend seo_rankings.SeoBacklinkReferringDomain"""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot, on_delete=models.CASCADE,
        related_name='referring_domain_rows', db_column='snapshot_id',
    )
    domain_name = models.CharField(max_length=255)
    rank = models.IntegerField(default=0)
    backlinks = models.IntegerField(default=0)
    backlinks_spam_score = models.IntegerField(default=0)
    broken_backlinks = models.IntegerField(default=0)
    referring_pages = models.IntegerField(default=0)
    referring_domains = models.IntegerField(default=0)
    first_seen = models.DateTimeField(null=True, blank=True)
    lost_date = models.DateTimeField(null=True, blank=True)
    country = models.CharField(max_length=8, blank=True, default='')
    is_new = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_backlink_referring_domains'
        managed = False


class SeoBacklinkAnchor(models.Model):
    """Mirror of backend seo_rankings.SeoBacklinkAnchor"""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot, on_delete=models.CASCADE,
        related_name='anchor_rows', db_column='snapshot_id',
    )
    anchor = models.TextField()
    rank = models.IntegerField(default=0)
    backlinks = models.IntegerField(default=0)
    backlinks_spam_score = models.IntegerField(default=0)
    referring_domains = models.IntegerField(default=0)
    referring_main_domains = models.IntegerField(default=0)
    referring_pages = models.IntegerField(default=0)
    first_seen = models.DateTimeField(null=True, blank=True)
    lost_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_backlink_anchors'
        managed = False


class SeoBacklinkPage(models.Model):
    """Mirror of backend seo_rankings.SeoBacklinkPage"""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot, on_delete=models.CASCADE,
        related_name='page_rows', db_column='snapshot_id',
    )
    page_url = models.TextField()
    rank = models.IntegerField(default=0)
    backlinks = models.IntegerField(default=0)
    referring_domains = models.IntegerField(default=0)
    referring_main_domains = models.IntegerField(default=0)
    referring_pages = models.IntegerField(default=0)
    status_code = models.IntegerField(null=True, blank=True)
    first_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_backlink_pages'
        managed = False


class SeoBacklinkHistoryPoint(models.Model):
    """Mirror of backend seo_rankings.SeoBacklinkHistoryPoint"""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot, on_delete=models.CASCADE,
        related_name='history_points', db_column='snapshot_id',
    )
    point_date = models.DateField()
    rank = models.IntegerField(default=0)
    backlinks = models.BigIntegerField(default=0)
    new_backlinks = models.IntegerField(default=0)
    lost_backlinks = models.IntegerField(default=0)
    new_referring_domains = models.IntegerField(default=0)
    lost_referring_domains = models.IntegerField(default=0)
    referring_domains = models.IntegerField(default=0)
    referring_main_domains = models.IntegerField(default=0)
    referring_pages = models.BigIntegerField(default=0)
    referring_ips = models.IntegerField(default=0)
    broken_backlinks = models.IntegerField(default=0)
    broken_pages = models.IntegerField(default=0)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_backlink_history_points'
        managed = False
