"""
SEO Rankings shared models for the engine.
These are unmanaged (managed=False) mirrors of the backend seo_rankings tables.
"""
from django.db import models


class SeoKeywordRank(models.Model):
    """Mirror of backend seo_rankings.SeoKeywordRank"""
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
        'shared_models.Keyword',
        on_delete=models.CASCADE,
        related_name='engine_seo_ranks',
        db_column='keyword_id',
    )
    domain_id = models.IntegerField()
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='desktop')

    rank_now = models.IntegerField(default=0)
    top_rank = models.IntegerField(null=True, blank=True)
    rank_since_start = models.IntegerField(default=0)

    day_val = models.IntegerField(default=0)
    day_mark = models.CharField(max_length=5, default='-')
    week_val = models.IntegerField(default=0)
    week_mark = models.CharField(max_length=5, default='-')
    half_month_val = models.IntegerField(default=0)
    half_month_mark = models.CharField(max_length=5, default='-')
    month_val = models.IntegerField(default=0)
    month_mark = models.CharField(max_length=5, default='-')
    status_from_start = models.CharField(max_length=5, default='-')

    featured_snippet = models.BooleanField(default=False)
    knowledge_panel = models.BooleanField(default=False)
    ads = models.BooleanField(default=False)
    review = models.BooleanField(default=False)
    total_rating = models.CharField(max_length=5, blank=True, default='-')
    total_review = models.CharField(max_length=15, blank=True, default='-')

    snippets_details = models.JSONField(default=dict, blank=True)
    keyword_snippet = models.JSONField(default=dict, blank=True)

    gsc_clicks = models.IntegerField(default=0)
    gsc_impressions = models.IntegerField(default=0)

    site_url = models.CharField(max_length=500, blank=True, default='')
    target_url = models.CharField(max_length=500, blank=True, default='')
    search_results = models.CharField(max_length=50, blank=True, default='-')
    search_volume = models.IntegerField(null=True, blank=True)

    region = models.CharField(max_length=20, default='google.com')
    isocode = models.CharField(max_length=5, default='us')
    language_code = models.CharField(max_length=8, default='en')
    geo_target = models.CharField(max_length=255, blank=True, default='')
    geo_target_uule = models.CharField(max_length=500, blank=True, default='')
    crawl_url = models.TextField(blank=True, default='')

    auto_call_status = models.CharField(max_length=5, choices=CALL_STATUS_CHOICES, default='avail')
    auto_refresh_count = models.IntegerField(default=0)
    manual_call_status = models.BooleanField(default=False)
    last_ranked_date = models.DateTimeField(null=True, blank=True)

    cannibalisation = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_keyword_ranks'
        managed = False

    def __str__(self):
        return f"SeoKeywordRank {self.id} [{self.platform}] rank={self.rank_now}"


class SeoRankHistory(models.Model):
    """Mirror of backend seo_rankings.SeoRankHistory"""
    seo_keyword_rank = models.ForeignKey(
        SeoKeywordRank,
        on_delete=models.CASCADE,
        related_name='engine_rank_history',
        db_column='seo_keyword_rank_id',
    )
    rank_position = models.IntegerField()
    snapshot_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_rank_history'
        managed = False

    def __str__(self):
        return f"RankHistory {self.seo_keyword_rank_id} -> {self.rank_position} on {self.snapshot_date}"


class SeoSerpFeatureHistory(models.Model):
    """Mirror of backend seo_rankings.SeoSerpFeatureHistory"""
    seo_keyword_rank = models.ForeignKey(
        SeoKeywordRank,
        on_delete=models.CASCADE,
        related_name='engine_serp_feature_history',
        db_column='seo_keyword_rank_id',
    )
    featured_snippet_url_list = models.JSONField(default=list, blank=True)
    featured_snippet_history = models.JSONField(default=dict, blank=True)
    new_featured_snippet_date = models.DateTimeField(null=True, blank=True)
    ad_snippet_url_list = models.JSONField(default=list, blank=True)
    ad_snippet_history = models.JSONField(default=dict, blank=True)
    new_ad_snippet_date = models.DateTimeField(null=True, blank=True)
    url_status = models.CharField(max_length=5, default='CMN')
    other_history = models.JSONField(default=dict, blank=True)
    comp_today = models.JSONField(default=dict, blank=True)
    ratings_changed_date = models.DateTimeField(null=True, blank=True)
    top_ratings = models.CharField(max_length=5, default='-')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_serp_feature_history'
        managed = False


class SeoDomainDailyMetrics(models.Model):
    """Mirror of backend seo_rankings.SeoDomainDailyMetrics"""
    domain_id = models.IntegerField()
    score_meter = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    top_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    improved_count = models.IntegerField(default=0)
    declined_count = models.IntegerField(default=0)
    no_change_count = models.IntegerField(default=0)
    activity_level = models.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    top_1_count = models.IntegerField(default=0)
    top_3_count = models.IntegerField(default=0)
    top_10_count = models.IntegerField(default=0)
    top_50_count = models.IntegerField(default=0)
    top_100_count = models.IntegerField(default=0)
    not_ranked_count = models.IntegerField(default=0)
    desktop_count = models.IntegerField(default=0)
    mobile_count = models.IntegerField(default=0)
    rating_0_2 = models.IntegerField(default=0)
    rating_2_4 = models.IntegerField(default=0)
    rating_4_5 = models.IntegerField(default=0)
    ads_you_above_below = models.IntegerField(default=0)
    ads_you_above = models.IntegerField(default=0)
    ads_you_below = models.IntegerField(default=0)
    ads_others_above_below = models.IntegerField(default=0)
    ads_others_above = models.IntegerField(default=0)
    ads_others_below = models.IntegerField(default=0)
    total_keywords = models.IntegerField(default=0)
    snapshot_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_domain_daily_metrics'
        managed = False


class SeoCompetitorAnalysis(models.Model):
    """Mirror of backend seo_rankings.SeoCompetitorAnalysis"""
    domain_id = models.IntegerField()
    status = models.CharField(max_length=5, default='INIT')
    total_keywords = models.IntegerField(default=0)
    unique_domains = models.IntegerField(default=0)
    total_domain_hits = models.IntegerField(default=0)
    analysis_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_competitor_analysis'
        managed = False


class SeoKeywordVolume(models.Model):
    """Mirror of backend seo_rankings.SeoKeywordVolume.

    One row per tracked keyword holding the Google Ads search-volume figures
    fetched from DataForSEO: the headline average, the 12-month series behind
    it, and the competition band.

    month_wise_volume / month_labels are stored oldest-first so the Volume
    History chart reads left-to-right. DataForSEO returns them newest-first, so
    the writer reverses them.
    """
    seo_keyword_rank = models.OneToOneField(
        SeoKeywordRank,
        on_delete=models.CASCADE,
        related_name='volume_data',
        db_column='seo_keyword_rank_id',
    )
    average_volume = models.IntegerField(default=0)
    top_volume = models.IntegerField(default=0)
    low_volume = models.IntegerField(default=0)
    comp_level = models.CharField(max_length=20, default='-')
    comp_index = models.CharField(max_length=10, default='-')
    month_wise_volume = models.JSONField(default=list, blank=True)
    month_labels = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'shared_models'
        db_table = 'seo_keyword_volumes'
        managed = False

    def __str__(self):
        return f"Volume {self.seo_keyword_rank_id}: avg={self.average_volume}"
