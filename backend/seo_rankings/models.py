from django.db import models


class SeoKeywordRank(models.Model):
    """
    Core SEO ranking data per keyword.
    Links to existing keywords.Keyword via FK — does NOT modify that table.
    Ported from Rankmax MongoDB 'keyword' collection (rank-specific fields only).
    """
    PLATFORM_CHOICES = [
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
    ]
    CALL_STATUS_CHOICES = [
        ('avail', 'Available'),
        ('busy', 'Busy'),
        ('load', 'Loading'),
        ('read', 'Reading'),
        ('done', 'Done'),
        ('fail', 'Failed'),
    ]

    keyword = models.ForeignKey(
        'keywords.Keyword',
        on_delete=models.CASCADE,
        related_name='seo_ranks',
        help_text="Link to the existing Promptmaxx keyword"
    )
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='seo_keyword_ranks',
        help_text="Domain this ranking belongs to"
    )
    platform = models.CharField(
        max_length=10,
        choices=PLATFORM_CHOICES,
        default='desktop',
        help_text="Device type: desktop or mobile"
    )

    # Current rank state
    rank_now = models.IntegerField(
        default=0,
        help_text="Current rank position (0 = not ranked)"
    )
    top_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Best rank ever achieved"
    )
    rank_since_start = models.IntegerField(
        default=0,
        help_text="Rank when keyword was first added"
    )

    # Change indicators (computed from rank history)
    day_val = models.IntegerField(default=0, help_text="Rank change vs 1 day ago (absolute)")
    day_mark = models.CharField(max_length=5, default='-', help_text="up/down/-")
    week_val = models.IntegerField(default=0, help_text="Rank change vs 7 days ago")
    week_mark = models.CharField(max_length=5, default='-')
    half_month_val = models.IntegerField(default=0, help_text="Rank change vs 15 days ago")
    half_month_mark = models.CharField(max_length=5, default='-')
    month_val = models.IntegerField(default=0, help_text="Rank change vs 30 days ago")
    month_mark = models.CharField(max_length=5, default='-')
    status_from_start = models.CharField(max_length=5, default='-', help_text="up/down/- since start")

    # SERP feature flags
    featured_snippet = models.BooleanField(default=False)
    knowledge_panel = models.BooleanField(default=False)
    ads = models.BooleanField(default=False)
    review = models.BooleanField(default=False)
    total_rating = models.CharField(max_length=5, blank=True, default='-')
    total_review = models.CharField(max_length=15, blank=True, default='-')

    # SERP details (replaces MongoDB DictField)
    snippets_details = models.JSONField(default=dict, blank=True, help_text="Full SERP feature data")
    keyword_snippet = models.JSONField(
        default=dict, blank=True,
        help_text="Today and best snippet: {tdy: {}, best: {}}"
    )

    # GSC data
    gsc_clicks = models.IntegerField(default=0)
    gsc_impressions = models.IntegerField(default=0)

    # Search metadata
    site_url = models.CharField(max_length=500, blank=True, default='')
    target_url = models.CharField(max_length=500, blank=True, default='')
    search_results = models.CharField(max_length=50, blank=True, default='-')
    search_volume = models.IntegerField(null=True, blank=True)

    # Crawl configuration
    region = models.CharField(max_length=20, default='google.com')
    isocode = models.CharField(max_length=5, default='us')
    language_code = models.CharField(max_length=8, default='en')
    geo_target = models.CharField(max_length=255, blank=True, default='')
    geo_target_uule = models.CharField(max_length=500, blank=True, default='')
    crawl_url = models.TextField(blank=True, default='')

    # Engine tracking
    auto_call_status = models.CharField(
        max_length=5,
        choices=CALL_STATUS_CHOICES,
        default='avail',
        help_text="Engine processing status"
    )
    auto_refresh_count = models.IntegerField(default=0)
    manual_call_status = models.BooleanField(default=False)
    last_ranked_date = models.DateTimeField(null=True, blank=True)

    # Cannibalisation
    cannibalisation = models.JSONField(default=list, blank=True)

    # Tags & Favourite (ported from RankMax Keyword.tags / Keyword.favour)
    tags = models.JSONField(default=list, blank=True, help_text="List of tag strings")
    favour = models.IntegerField(default=0, help_text="0=unfavorite, 1=favorite")

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_keyword_ranks'
        verbose_name = 'SEO Keyword Rank'
        verbose_name_plural = 'SEO Keyword Ranks'
        unique_together = ['keyword', 'domain', 'platform']
        indexes = [
            models.Index(fields=['domain', 'platform', '-rank_now']),
            models.Index(fields=['domain', 'auto_call_status']),
            models.Index(fields=['domain', '-last_ranked_date']),
            models.Index(fields=['keyword', 'platform']),
        ]

    def __str__(self):
        return f"{self.keyword.keyword} [{self.platform}] → Rank {self.rank_now}"


class SeoRankHistory(models.Model):
    """
    Daily rank snapshots. Replaces Rankmax MongoDB keyword.rank[] array.
    One row per keyword per day — PostgreSQL-native approach.
    """
    seo_keyword_rank = models.ForeignKey(
        SeoKeywordRank,
        on_delete=models.CASCADE,
        related_name='rank_history'
    )
    rank_position = models.IntegerField(
        help_text="Rank position on this date (0 = not ranked)"
    )
    snapshot_date = models.DateField(help_text="Date of this rank snapshot")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seo_rank_history'
        verbose_name = 'SEO Rank History'
        verbose_name_plural = 'SEO Rank Histories'
        unique_together = ['seo_keyword_rank', 'snapshot_date']
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['seo_keyword_rank', '-snapshot_date']),
        ]

    def __str__(self):
        return f"{self.seo_keyword_rank} → {self.rank_position} on {self.snapshot_date}"


class SeoSerpFeatureHistory(models.Model):
    """
    SERP feature history per keyword. Replaces Rankmax MongoDB 'keywordhistory' collection.
    Tracks featured snippets, ads, URL changes, rating changes over time.
    """
    seo_keyword_rank = models.ForeignKey(
        SeoKeywordRank,
        on_delete=models.CASCADE,
        related_name='serp_feature_history'
    )

    # Featured snippet tracking
    featured_snippet_url_list = models.JSONField(default=list, blank=True)
    featured_snippet_history = models.JSONField(default=dict, blank=True)
    new_featured_snippet_date = models.DateTimeField(null=True, blank=True)

    # Ad snippet tracking
    ad_snippet_url_list = models.JSONField(default=list, blank=True)
    ad_snippet_history = models.JSONField(default=dict, blank=True)
    new_ad_snippet_date = models.DateTimeField(null=True, blank=True)

    # URL and rating tracking
    url_status = models.CharField(max_length=5, default='CMN')
    other_history = models.JSONField(default=dict, blank=True)
    comp_today = models.JSONField(default=dict, blank=True)
    ratings_changed_date = models.DateTimeField(null=True, blank=True)
    top_ratings = models.CharField(max_length=5, default='-')

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_serp_feature_history'
        verbose_name = 'SEO SERP Feature History'
        verbose_name_plural = 'SEO SERP Feature Histories'
        indexes = [
            models.Index(fields=['seo_keyword_rank', '-modified_at']),
        ]

    def __str__(self):
        return f"SERP History: {self.seo_keyword_rank}"


class SeoDomainDailyMetrics(models.Model):
    """
    Daily aggregated SEO metrics per domain.
    Replaces Rankmax MongoDB group.score_meter[], activity_level[], since_start[] arrays.
    One row per domain per day — PostgreSQL-native approach.
    """
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='seo_daily_metrics'
    )

    # Rankmax score (weighted score based on rank positions)
    score_meter = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.0,
        help_text="Rankmax score: weighted score 0-100"
    )
    top_score = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Best Rankmax score ever achieved"
    )

    # Today's performance
    improved_count = models.IntegerField(default=0)
    declined_count = models.IntegerField(default=0)
    no_change_count = models.IntegerField(default=0)
    activity_level = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.0,
        help_text="((improved - declined) / total) * 100"
    )

    # Comparison buckets (Top 1, Top 3, Top 10, etc.)
    top_1_count = models.IntegerField(default=0)
    top_3_count = models.IntegerField(default=0)
    top_10_count = models.IntegerField(default=0)
    top_50_count = models.IntegerField(default=0)
    top_100_count = models.IntegerField(default=0)
    not_ranked_count = models.IntegerField(default=0)

    # Device split
    desktop_count = models.IntegerField(default=0)
    mobile_count = models.IntegerField(default=0)

    # SERP Features — Your Ratings (ported from RankMax R2, R4, R5)
    rating_0_2 = models.IntegerField(default=0, help_text="Keywords with 0-2 star ratings")
    rating_2_4 = models.IntegerField(default=0, help_text="Keywords with 2-4 star ratings")
    rating_4_5 = models.IntegerField(default=0, help_text="Keywords with 4-5 star ratings")

    # Google Search Ads — Your ads (ported from RankMax Ay)
    ads_you_above_below = models.IntegerField(default=0, help_text="Your ads: above & below fold")
    ads_you_above = models.IntegerField(default=0, help_text="Your ads: above fold only")
    ads_you_below = models.IntegerField(default=0, help_text="Your ads: below fold only")

    # Google Search Ads — Others' ads (ported from RankMax Ao)
    ads_others_above_below = models.IntegerField(default=0, help_text="Others' ads: above & below fold")
    ads_others_above = models.IntegerField(default=0, help_text="Others' ads: above fold only")
    ads_others_below = models.IntegerField(default=0, help_text="Others' ads: below fold only")

    # Total keywords tracked on this date
    total_keywords = models.IntegerField(default=0)

    snapshot_date = models.DateField(help_text="Date of this metrics snapshot")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_domain_daily_metrics'
        verbose_name = 'SEO Domain Daily Metrics'
        verbose_name_plural = 'SEO Domain Daily Metrics'
        unique_together = ['domain', 'snapshot_date']
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['domain', '-snapshot_date']),
        ]

    def __str__(self):
        return f"{self.domain.name} → Score {self.score_meter} on {self.snapshot_date}"


class SeoCompetitorAnalysis(models.Model):
    """
    Tracks one competitor analysis run per domain.
    Status machine: INIT → SCHD (analyzing) → COMP (candidates ready) → FAIL
    """
    STATUS_CHOICES = [
        ('INIT', 'Not started'),
        ('SCHD', 'Analyzing'),
        ('COMP', 'Completed'),
        ('FAIL', 'Failed'),
    ]
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='comp_analyses',
    )
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default='INIT')
    total_keywords = models.IntegerField(default=0)
    unique_domains = models.IntegerField(default=0)
    total_domain_hits = models.IntegerField(default=0)
    analysis_json = models.JSONField(
        default=dict, blank=True,
        help_text="Aggregated data: {domains: {domain: count}, keys: {domain: [kw_ids]}}"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_competitor_analysis'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.domain.name} competitor analysis — {self.status}"


class SeoCompetitorProject(models.Model):
    """A competitor domain actively tracked for a project (max 6 per domain)."""
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='comp_projects',
    )
    competitor_domain = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_competitor_project'
        unique_together = ['domain', 'competitor_domain']
        ordering = ['competitor_domain']

    def __str__(self):
        return f"{self.domain.name} → {self.competitor_domain}"


class SeoCompetitorKeyword(models.Model):
    """Keyword rank comparison: our domain vs a tracked competitor."""
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='comp_kw_rows',
    )
    competitor = models.ForeignKey(
        SeoCompetitorProject,
        on_delete=models.CASCADE,
        related_name='keywords',
    )
    seo_keyword_rank = models.ForeignKey(
        'SeoKeywordRank',
        on_delete=models.CASCADE,
        related_name='comp_kw_rows',
    )
    keyword_text = models.TextField()
    our_rank = models.IntegerField(default=0)
    their_rank = models.IntegerField(default=0)
    our_url = models.TextField(blank=True, default='')
    their_url = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_competitor_keyword'
        unique_together = ['competitor', 'seo_keyword_rank']
        ordering = ['our_rank', 'keyword_text']

    def __str__(self):
        return f"{self.keyword_text}: us={self.our_rank} vs {self.competitor.competitor_domain}={self.their_rank}"


class SeoReportSheet(models.Model):
    """
    SEO Report sheet configuration. Ported from RankMax ReportSheets model.
    Each sheet defines a report tab with its type, metrics, schedule, and display settings.
    """
    SHEET_TYPE_CHOICES = [
        ('gsc_queries', 'GSC Queries'),
        ('gsc_branded_queries', 'GSC Branded Queries'),
        ('gsc_non_branded_queries', 'GSC Non-Branded Queries'),
        ('gsc_pages', 'GSC Pages'),
        ('ga_landing_pages', 'GA Landing Pages'),
        ('ga_other_sources', 'GA Other Sources'),
        ('ga_gsc_reconcile', 'GA vs GSC Reconciliation'),
        ('ga_overview', 'GA Overview'),
        ('keyword_ranking', 'Keyword Ranking'),
        ('domain_metrics', 'Domain Metrics'),
        ('gsc_overview', 'GSC Overview'),
        ('keyword_ranking_overview', 'Keyword Ranking Overview'),
    ]
    SCHEDULE_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    CATEGORY_CHOICES = [
        ('gsc', 'Google Search Console'),
        ('ga', 'Google Analytics'),
        ('rank', 'Keyword Ranking'),
        ('base', 'Domain Metrics'),
        ('overview', 'Summary'),
    ]

    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='seo_report_sheets',
        help_text="Domain this report belongs to"
    )
    created_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.CASCADE,
        related_name='seo_report_sheets',
    )
    sheet_name = models.CharField(max_length=255, help_text="Report display name")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='gsc',
        help_text="Report category tab"
    )
    sheet_type = models.CharField(
        max_length=30,
        choices=SHEET_TYPE_CHOICES,
        help_text="Type of data in this report sheet"
    )
    metrics = models.JSONField(
        default=list, blank=True,
        help_text="Selected metrics for the report"
    )
    change_units = models.JSONField(
        default=list, blank=True,
        help_text="Comparison units: number, percentage"
    )
    schedule = models.CharField(
        max_length=10,
        choices=SCHEDULE_CHOICES,
        default='weekly',
    )
    duration = models.IntegerField(
        default=2,
        help_text="Number of intervals to include"
    )
    order_by = models.CharField(
        max_length=20,
        default='Ascending',
        help_text="Date sort order"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_report_sheets'
        verbose_name = 'SEO Report Sheet'
        verbose_name_plural = 'SEO Report Sheets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', '-created_at']),
            models.Index(fields=['domain', 'category']),
        ]

    def __str__(self):
        return f"{self.sheet_name} [{self.category}] — {self.domain.name}"


class SeoKeywordNote(models.Model):
    """
    Notes attached to a keyword. Ported from RankMax kwNotes model.
    Allows users to annotate keywords with observations, reminders, etc.
    """
    seo_keyword_rank = models.ForeignKey(
        SeoKeywordRank,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        related_name='seo_keyword_notes',
    )
    created_by = models.ForeignKey(
        'authentication.Account',
        on_delete=models.CASCADE,
        related_name='seo_keyword_notes',
    )
    title = models.CharField(max_length=100)
    notes = models.TextField()
    note_date = models.DateField(help_text="Date the note refers to")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_keyword_notes'
        verbose_name = 'SEO Keyword Note'
        verbose_name_plural = 'SEO Keyword Notes'
        ordering = ['-note_date', '-created_at']
        indexes = [
            models.Index(fields=['seo_keyword_rank', '-note_date']),
        ]

    def __str__(self):
        return f"{self.title} — {self.note_date}"


class SeoKeywordVolume(models.Model):
    """
    Search volume history per keyword. Ported from RankMax keywordVolume model.
    Tracks monthly search volumes and competition data.
    """
    seo_keyword_rank = models.OneToOneField(
        SeoKeywordRank,
        on_delete=models.CASCADE,
        related_name='volume_data',
    )
    average_volume = models.IntegerField(default=0, help_text="Average monthly search volume")
    top_volume = models.IntegerField(default=0, help_text="Highest monthly volume in the period")
    low_volume = models.IntegerField(default=0, help_text="Lowest monthly volume in the period")
    comp_level = models.CharField(
        max_length=20, default='-',
        help_text="Competition level: Low/Medium/High/UNSPECIFIED"
    )
    comp_index = models.CharField(
        max_length=10, default='-',
        help_text="Competition index: 0-100 or -"
    )
    month_wise_volume = models.JSONField(
        default=list, blank=True,
        help_text="Array of monthly search volumes, e.g. [20, 30, 30, 30, 210, 260]"
    )
    month_labels = models.JSONField(
        default=list, blank=True,
        help_text="Array of month labels, e.g. ['June', 'August', 'October', ...]"
    )
    status = models.CharField(
        max_length=10, default='new',
        help_text="Volume fetch status: new/done/fail"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seo_keyword_volumes'
        verbose_name = 'SEO Keyword Volume'
        verbose_name_plural = 'SEO Keyword Volumes'

    def __str__(self):
        return f"Volume for {self.seo_keyword_rank}: avg={self.average_volume}"
