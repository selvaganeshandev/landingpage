"""
Backlink profile storage — DataForSEO Backlinks API.

Unlike rank tracking, nothing here is on a schedule. A fetch happens only when
a user presses "Fetch backlinks", and is then rate-limited to once per calendar
month per project (see ``SeoBacklinkSnapshot.next_refresh_allowed_at``). That
constraint is a *cost* control, not a technical one: a single full pull of a
large domain costs several dollars against a shared prepaid balance, so the
guard lives in the database where the API cannot be talked out of it.

The unit of storage is a **snapshot** — one complete fetch of one domain at one
point in time. Snapshots are never mutated after they complete, so month-over-
month comparison is just two rows, and a failed fetch cannot corrupt the last
good profile.
"""
from django.db import models


class SeoBacklinkSnapshot(models.Model):
    """One complete backlink pull for one domain.

    Rows are created in ``PEND`` before any money is spent, flipped to ``RUN``
    while the API is being paged through, and only then to ``DONE``. A row stuck
    in ``RUN`` is how a crashed worker is detected — the UI shows it as still
    loading, and ``stale_running()`` reclaims it.
    """
    STATUS_CHOICES = [
        ('PEND', 'Queued'),
        ('RUN', 'Fetching'),
        ('DONE', 'Complete'),
        ('FAIL', 'Failed'),
    ]

    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='backlink_snapshots',
    )
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='PEND')
    requested_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='backlink_snapshots_requested',
        help_text="Who pressed Fetch — every snapshot is user-initiated.",
    )

    # ----- Profile summary (/v3/backlinks/summary/live) -----
    # Field names mirror the API response so the mapping stays checkable by eye.
    rank = models.IntegerField(default=0, help_text="Domain authority 0-1000")
    backlinks = models.BigIntegerField(default=0)
    backlinks_spam_score = models.IntegerField(default=0, help_text="0-100, higher is worse")
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

    # The API returns these six already aggregated, so the whole breakdown
    # section of the page costs no extra calls and needs no extra tables.
    referring_links_tld = models.JSONField(default=dict, blank=True)
    referring_links_types = models.JSONField(default=dict, blank=True)
    referring_links_attributes = models.JSONField(default=dict, blank=True)
    referring_links_platform_types = models.JSONField(default=dict, blank=True)
    referring_links_semantic_locations = models.JSONField(default=dict, blank=True)
    referring_links_countries = models.JSONField(default=dict, blank=True)

    target_info = models.JSONField(
        default=dict, blank=True,
        help_text="The summary `info` block: server, cms, platform_type, ip.",
    )

    # ----- Fetch bookkeeping -----
    # Stored per snapshot because the balance is shared and prepaid; without
    # this there is no way to answer "what did last month's refresh cost us".
    api_cost = models.DecimalField(
        max_digits=10, decimal_places=6, default=0,
        help_text="USD actually billed by DataForSEO for this snapshot.",
    )
    api_requests = models.IntegerField(default=0, help_text="HTTP calls made")
    is_truncated = models.BooleanField(
        default=False,
        help_text=(
            "True when the domain has more backlinks than MAX_BACKLINK_ROWS and "
            "only the highest-ranked ones were stored. The summary counts above "
            "are still the true totals — only the detail table is partial."
        ),
    )
    error_message = models.TextField(blank=True, default='')

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    next_refresh_allowed_at = models.DateTimeField(
        null=True, blank=True,
        help_text=(
            "Set on completion to completed_at + REFRESH_INTERVAL_DAYS. The UI "
            "shows this date verbatim in the 'you can refresh again on …' alert."
        ),
    )

    class Meta:
        db_table = 'seo_backlink_snapshots'
        verbose_name = 'SEO Backlink Snapshot'
        verbose_name_plural = 'SEO Backlink Snapshots'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['domain', '-started_at']),
            models.Index(fields=['domain', 'status', '-completed_at']),
        ]

    def __str__(self):
        return f"{self.domain_id} backlinks @ {self.started_at:%Y-%m-%d} [{self.status}]"


class SeoBacklinkItem(models.Model):
    """One inbound link (/v3/backlinks/backlinks/live).

    The largest table by far — capped per snapshot by MAX_BACKLINK_ROWS.
    """
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot,
        on_delete=models.CASCADE,
        related_name='items',
    )

    domain_from = models.CharField(max_length=255, db_index=True)
    url_from = models.TextField()
    url_to = models.TextField()
    tld_from = models.CharField(max_length=63, blank=True, default='')

    anchor = models.TextField(blank=True, default='')
    # `item_type` is anchor | image | canonical | redirect | alternate — what
    # kind of markup carries the link, not what kind of page it sits on.
    item_type = models.CharField(max_length=20, blank=True, default='')
    dofollow = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    is_broken = models.BooleanField(default=False)
    is_indirect_link = models.BooleanField(default=False)

    rank = models.IntegerField(default=0, help_text="Strength of this individual link")
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

    # How many keywords the *linking* page ranks for — the cheapest available
    # proxy for whether a link sits on a page anyone actually reaches.
    ranked_keywords_info = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'seo_backlink_items'
        verbose_name = 'SEO Backlink'
        verbose_name_plural = 'SEO Backlinks'
        ordering = ['-rank']
        indexes = [
            models.Index(fields=['snapshot', '-rank']),
            models.Index(fields=['snapshot', 'dofollow']),
            models.Index(fields=['snapshot', 'is_new']),
            models.Index(fields=['snapshot', 'is_lost']),
            models.Index(fields=['snapshot', '-backlink_spam_score']),
        ]

    def __str__(self):
        return f"{self.domain_from} → {self.url_to}"


class SeoBacklinkReferringDomain(models.Model):
    """A linking domain, aggregated (/v3/backlinks/referring_domains/live)."""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot,
        on_delete=models.CASCADE,
        related_name='referring_domain_rows',
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
        db_table = 'seo_backlink_referring_domains'
        ordering = ['-rank']
        indexes = [models.Index(fields=['snapshot', '-rank'])]

    def __str__(self):
        return f"{self.domain_name} ({self.backlinks} links)"


class SeoBacklinkAnchor(models.Model):
    """An anchor text and its aggregate stats (/v3/backlinks/anchors/live)."""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot,
        on_delete=models.CASCADE,
        related_name='anchor_rows',
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
        db_table = 'seo_backlink_anchors'
        ordering = ['-backlinks']
        indexes = [models.Index(fields=['snapshot', '-backlinks'])]

    def __str__(self):
        return f"{self.anchor[:50]} ({self.backlinks})"


class SeoBacklinkPage(models.Model):
    """A page on the target that receives links (/v3/backlinks/domain_pages/live)."""
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot,
        on_delete=models.CASCADE,
        related_name='page_rows',
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
        db_table = 'seo_backlink_pages'
        ordering = ['-backlinks']
        indexes = [models.Index(fields=['snapshot', '-backlinks'])]

    def __str__(self):
        return f"{self.page_url} ({self.backlinks})"


class SeoBacklinkHistoryPoint(models.Model):
    """One month of the profile's history (/v3/backlinks/history/live).

    Kept as its own table rather than a JSON blob on the snapshot because the
    chart is the one part of this page that reads across months, and because
    DataForSEO backfills years of history in a single call — so even a first
    fetch draws a full trend line rather than a single dot.
    """
    snapshot = models.ForeignKey(
        SeoBacklinkSnapshot,
        on_delete=models.CASCADE,
        related_name='history_points',
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
        db_table = 'seo_backlink_history_points'
        unique_together = ['snapshot', 'point_date']
        ordering = ['point_date']
        indexes = [models.Index(fields=['snapshot', 'point_date'])]

    def __str__(self):
        return f"{self.point_date}: {self.backlinks} backlinks"
