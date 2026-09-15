"""Audit Engine shared models for the engine.

Unmanaged (managed=False) mirrors of the backend `audits` tables, in the same
style as seo_models.py: the backend's migration creates the tables, the engine
only reads and writes them. Field lists must stay in sync with
backend/audits/models.py — the worker fills these rows stage by stage.
"""
from django.db import models
from django.utils import timezone


class Audit(models.Model):
    """Mirror of backend audits.Audit"""
    STATUS_CHOICES = [
        ('INIT', 'Queued'),
        ('PROC', 'Processing'),
        ('DONE', 'Published'),
        ('FAIL', 'Failed'),
    ]
    STAGE_ORDER = ['profile', 'crawl', 'prompts', 'engines', 'serp', 'score', 'publish']

    public_token = models.CharField(max_length=32, unique=True, editable=False)
    host = models.CharField(max_length=255)
    website = models.URLField()
    country = models.CharField(max_length=2, default='us')
    source = models.CharField(max_length=8, default='manual')

    requested_by = models.ForeignKey(
        'shared_models.Account', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', db_constraint=False,
    )
    requester_email = models.EmailField(blank=True, default='')
    requester_ip = models.GenericIPAddressField(null=True, blank=True)

    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='INIT')
    stage = models.CharField(max_length=16, blank=True, default='')
    progress = models.PositiveSmallIntegerField(default=0)
    stage_detail = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default='')

    brand_name = models.CharField(max_length=255, blank=True, default='')
    industry = models.CharField(max_length=255, blank=True, default='')
    competitors = models.JSONField(default=list, blank=True)
    tech_stack = models.JSONField(default=list, blank=True)
    grounding = models.JSONField(default=dict, blank=True)

    geo_score = models.PositiveSmallIntegerField(null=True, blank=True)
    geo_stage = models.CharField(max_length=10, blank=True, default='')
    appearances = models.PositiveIntegerField(default=0)
    cited_runs = models.PositiveIntegerField(default=0)
    total_runs = models.PositiveIntegerField(default=0)
    engines_preferred = models.PositiveSmallIntegerField(default=0)
    engines_total = models.PositiveSmallIntegerField(default=0)
    share_of_voice = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    seo_visibility = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    keywords_top10 = models.PositiveSmallIntegerField(default=0)
    keywords_total = models.PositiveSmallIntegerField(default=0)

    report = models.JSONField(default=dict, blank=True)

    opens = models.PositiveIntegerField(default=0)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_by = models.ForeignKey(
        'shared_models.Account', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', db_constraint=False,
    )
    claimed_domain = models.ForeignKey(
        'shared_models.Domain', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', db_constraint=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'audits'
        managed = False
        ordering = ['-created_at']

    def __str__(self):
        return f"Audit {self.pk} for {self.host} ({self.status})"

    def set_stage(self, stage, progress=None, **detail):
        """Advance the pipeline. Mirrors the backend helper so the worker can use it."""
        if stage not in self.STAGE_ORDER:
            raise ValueError(f"unknown audit stage {stage!r}")
        self.stage = stage
        if progress is None:
            progress = int(100 * self.STAGE_ORDER.index(stage) / len(self.STAGE_ORDER))
        self.progress = max(0, min(100, int(progress)))
        if detail:
            merged = dict(self.stage_detail or {})
            merged[stage] = {**merged.get(stage, {}), **detail}
            self.stage_detail = merged
        if self.status == 'INIT':
            self.status = 'PROC'
        self.save(update_fields=['stage', 'progress', 'stage_detail', 'status', 'modified_at'])

    def mark_failed(self, error):
        self.status = 'FAIL'
        self.error = (error or '')[:4000]
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error', 'completed_at', 'modified_at'])


class AuditPromptResult(models.Model):
    """Mirror of backend audits.AuditPromptResult"""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='prompt_results', db_constraint=False)
    prompt_index = models.PositiveSmallIntegerField()
    prompt_text = models.TextField()
    topic = models.CharField(max_length=255, blank=True, default='')
    funnel_stage = models.CharField(max_length=6, blank=True, default='')
    platform = models.CharField(max_length=32)
    run_index = models.PositiveSmallIntegerField(default=1)

    status = models.CharField(max_length=12, default='ok')
    is_mention = models.BooleanField(default=False)
    is_cited = models.BooleanField(default=False)
    position = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sentiment = models.CharField(max_length=8, blank=True, default='')
    competitors_mentioned = models.JSONField(default=list, blank=True)
    rival_positions = models.JSONField(default=dict, blank=True)
    cited_domains = models.JSONField(default=list, blank=True)
    response_text = models.TextField(blank=True, default='')
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_prompt_results'
        managed = False
        ordering = ['audit', 'prompt_index', 'platform', 'run_index']
        unique_together = [('audit', 'prompt_index', 'platform', 'run_index')]

    def __str__(self):
        return f"Audit {self.audit_id} prompt {self.prompt_index} on {self.platform}"


class AuditKeywordResult(models.Model):
    """Mirror of backend audits.AuditKeywordResult"""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='keyword_results', db_constraint=False)
    keyword = models.CharField(max_length=255)
    search_volume = models.PositiveIntegerField(null=True, blank=True)
    position = models.PositiveSmallIntegerField(null=True, blank=True)
    ranking_url = models.URLField(max_length=1000, blank=True, default='')
    outranked_by = models.JSONField(default=list, blank=True)
    serp_features = models.JSONField(default=list, blank=True)
    geo_engines_mentioning = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_keyword_results'
        managed = False
        ordering = ['audit', '-search_volume']
        unique_together = [('audit', 'keyword')]

    def __str__(self):
        return f"Audit {self.audit_id} keyword '{self.keyword}' pos {self.position}"


class AuditPageResult(models.Model):
    """Mirror of backend audits.AuditPageResult"""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='page_results', db_constraint=False)
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=255, blank=True, default='')
    fetched = models.BooleanField(default=True)
    error = models.CharField(max_length=200, blank=True, default='')
    word_count = models.PositiveIntegerField(default=0)
    schema_types = models.JSONField(default=list, blank=True)
    author = models.CharField(max_length=120, blank=True, default='')
    external_links = models.PositiveSmallIntegerField(default=0)
    last_modified = models.DateField(null=True, blank=True)
    question_headings = models.PositiveSmallIntegerField(default=0)
    has_table = models.BooleanField(default=False)
    has_faq_schema = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_page_results'
        managed = False
        ordering = ['audit', 'id']
        unique_together = [('audit', 'url')]

    def __str__(self):
        return f"Audit {self.audit_id} page {self.url}"
