"""Audit Engine — a URL goes in, a public GEO + SEO audit comes out.

An audit is the pre-signup twin of a tracked Domain: it runs the same site
crawl, prompt generation, LLM measurement and SERP lookup, but against a site
that has no Domain row, no organisation and (usually) no logged-in user. The
result is published at a public token URL and can later be "claimed", which
creates the Domain and links it back here as the Day-0 baseline.

Handoff follows the PromptGenerationRun pattern: the backend API creates the
row with status INIT and returns; the engine's worker walks the six stages,
updating `stage`/`progress`/`stage_detail` so the UI can poll; the row ends
DONE or FAIL. Per-prompt and per-keyword evidence lives in the two child
tables so every number on the report can be clicked through to its runs.

Nothing here is wired into scheduling or beat — an audit only runs when a
task is explicitly enqueued for it.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def _new_public_token():
    # 16 random bytes -> 22 URL-safe chars. Unguessable; this is the only
    # credential a public report has.
    return secrets.token_urlsafe(16)


class Audit(models.Model):
    STATUS_CHOICES = [
        ('INIT', 'Queued'),
        ('PROC', 'Processing'),
        ('DONE', 'Published'),
        ('FAIL', 'Failed'),
    ]

    # The six pipeline stages, in order. `stage` drives the progress UI.
    STAGE_CHOICES = [
        ('profile', 'Reading the site'),
        ('crawl', 'Checking your pages'),
        ('prompts', 'Writing buyer prompts'),
        ('engines', 'Asking the AI engines'),
        ('serp', 'Checking Google rankings'),
        ('score', 'Scoring'),
        ('publish', 'Publishing the report'),
    ]
    STAGE_ORDER = ['profile', 'crawl', 'prompts', 'engines', 'serp', 'score', 'publish']

    SOURCE_CHOICES = [
        ('manual', 'Run from the app'),
        ('landing', 'Landing page'),
        ('api', 'Public API'),
    ]

    # GEO score bands. Thresholds live in audits.scoring; the labels are stored
    # so the leads table and report never recompute them.
    GEO_STAGE_CHOICES = [
        ('absent', 'Absent'),
        ('present', 'Present'),
        ('preferred', 'Preferred'),
        ('default', 'Default'),
    ]

    # ---- identity ----
    public_token = models.CharField(
        max_length=32, unique=True, default=_new_public_token, editable=False,
        help_text="Unguessable slug for the public report URL",
    )
    host = models.CharField(
        max_length=255, db_index=True,
        help_text="Normalised hostname, e.g. 'hdfcbank.com' (no scheme, no www)",
    )
    website = models.URLField(help_text="Canonical URL the crawl started from")
    country = models.CharField(
        max_length=2, default='us',
        help_text="ISO 3166-1 alpha-2 market the prompts and SERP are run for",
    )
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES, default='manual')

    # ---- who asked ----
    # Manual audits carry the user; landing/API audits carry only an email (if
    # the visitor left one) and the IP used for rate limiting.
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audits_requested',
    )
    requester_email = models.EmailField(blank=True, default='')
    requester_ip = models.GenericIPAddressField(null=True, blank=True)

    # ---- pipeline state ----
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='INIT')
    stage = models.CharField(max_length=16, choices=STAGE_CHOICES, blank=True, default='')
    progress = models.PositiveSmallIntegerField(default=0, help_text="0-100")
    # Per-stage counters the progress screen shows, e.g.
    # {"engines": {"done": 61, "total": 144}, "serp": {"done": 118, "total": 200}}
    stage_detail = models.JSONField(default=dict, blank=True)
    # Everything the run was configured with (prompt count, engines, runs per
    # prompt, keyword count, SEO on/off). Stored so a re-run reproduces it and
    # so scores are comparable across audits run with the same settings.
    config = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default='')

    # ---- profile (stage 1 output) ----
    brand_name = models.CharField(max_length=255, blank=True, default='')
    industry = models.CharField(max_length=255, blank=True, default='')
    competitors = models.JSONField(
        default=list, blank=True,
        help_text="[{'name': 'ICICI Bank', 'host': 'icicibank.com'}, ...]",
    )
    tech_stack = models.JSONField(default=list, blank=True, help_text="['WordPress', 'Cloudflare']")
    # Crawl + extraction output, cached so a re-run or a claim skips the slow stage.
    grounding = models.JSONField(default=dict, blank=True)

    # ---- headline scores (stage 5 output) ----
    geo_score = models.PositiveSmallIntegerField(null=True, blank=True, help_text="0-100")
    geo_stage = models.CharField(max_length=10, choices=GEO_STAGE_CHOICES, blank=True, default='')
    appearances = models.PositiveIntegerField(default=0, help_text="Runs where the brand was mentioned")
    cited_runs = models.PositiveIntegerField(default=0, help_text="Runs where the brand's site was cited")
    total_runs = models.PositiveIntegerField(default=0, help_text="Runs that completed (denominator)")
    engines_preferred = models.PositiveSmallIntegerField(default=0, help_text="Engines mentioning the brand on >50% of prompts")
    engines_total = models.PositiveSmallIntegerField(default=0)
    share_of_voice = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percent")
    seo_visibility = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    keywords_top10 = models.PositiveSmallIntegerField(default=0)
    keywords_total = models.PositiveSmallIntegerField(default=0)

    # ---- report body (stage 5 output, rendered by the public page) ----
    # Shape is owned by audits.scoring.score_audit(); the page reads it verbatim.
    report = models.JSONField(default=dict, blank=True)

    # ---- publication ----
    opens = models.PositiveIntegerField(default=0, help_text="Public report views")
    last_opened_at = models.DateTimeField(null=True, blank=True)
    # Delivery. Publication no longer emails anyone by default, so the leads
    # table has to say whether the report actually reached someone and when.
    emailed_at = models.DateTimeField(null=True, blank=True, help_text="When the report was last emailed")
    emailed_to = models.JSONField(default=list, blank=True, help_text="Addresses the last send went to")
    email_count = models.PositiveIntegerField(default=0, help_text="How many times the report has been emailed")
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Public link stops resolving after this; claimed audits never expire",
    )

    # ---- claim ----
    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audits_claimed',
    )
    claimed_domain = models.ForeignKey(
        'domains.Domain', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audits',
        help_text="Domain created from this audit; the audit is its Day-0 baseline",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'audits'
        verbose_name = 'Audit'
        verbose_name_plural = 'Audits'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['host', '-created_at']),
            models.Index(fields=['source', '-created_at']),
            models.Index(fields=['requester_ip', '-created_at']),
        ]

    def __str__(self):
        return f"Audit {self.pk} for {self.host} ({self.status})"

    # ---- convenience ----

    @property
    def is_claimed(self):
        return self.claimed_domain_id is not None

    @property
    def is_expired(self):
        if self.is_claimed or self.expires_at is None:
            return False
        return timezone.now() >= self.expires_at

    @property
    def stage_index(self):
        """1-based position of `stage` in STAGE_ORDER; 0 when not started."""
        try:
            return self.STAGE_ORDER.index(self.stage) + 1
        except ValueError:
            return 0

    def set_stage(self, stage, progress=None, **detail):
        """Advance the pipeline. Progress defaults to the stage's share of 100."""
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

    def mark_done(self, ttl_days=None):
        if ttl_days is None:
            ttl_days = getattr(settings, 'AUDIT_PUBLIC_TTL_DAYS', 30)
        now = timezone.now()
        self.status = 'DONE'
        self.stage = 'publish'
        self.progress = 100
        self.completed_at = now
        self.error = ''
        if not self.expires_at:
            self.expires_at = now + timedelta(days=ttl_days)
        self.save(update_fields=[
            'status', 'stage', 'progress', 'completed_at', 'error', 'expires_at', 'modified_at',
        ])

    def mark_failed(self, error):
        self.status = 'FAIL'
        self.error = (error or '')[:4000]
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error', 'completed_at', 'modified_at'])

    def record_email(self, addresses):
        """Remember that the report was emailed, and to whom.

        Called after Mailgun accepts the message — by the "Email report" button
        and by the engine when AUDIT_AUTO_EMAIL_ON_PUBLISH sends one. Counting
        is done with F() so two sends at once cannot lose one.
        """
        addresses = [str(a).strip() for a in (addresses or []) if str(a).strip()][:5]
        type(self).objects.filter(pk=self.pk).update(
            emailed_at=timezone.now(), emailed_to=addresses,
            email_count=models.F('email_count') + 1, modified_at=timezone.now(),
        )
        self.refresh_from_db(fields=['emailed_at', 'emailed_to', 'email_count'])
        return self.emailed_at

    def record_open(self):
        """Count a public view without touching modified_at."""
        Audit.objects.filter(pk=self.pk).update(
            opens=models.F('opens') + 1, last_opened_at=timezone.now(),
        )


class AuditPromptResult(models.Model):
    """One prompt asked once on one engine — the evidence row behind the GEO score."""
    STATUS_CHOICES = [
        ('ok', 'Answered'),
        ('failed', 'Failed'),
        ('rate_limited', 'Rate limited'),
        ('skipped', 'Skipped'),
    ]
    FUNNEL_CHOICES = [
        ('top', 'Top'),
        ('middle', 'Middle'),
        ('bottom', 'Bottom'),
    ]
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='prompt_results')
    # Prompts are numbered within an audit so the report can group N engine
    # rows under one question without matching on free text.
    prompt_index = models.PositiveSmallIntegerField()
    prompt_text = models.TextField()
    topic = models.CharField(max_length=255, blank=True, default='')
    funnel_stage = models.CharField(max_length=6, choices=FUNNEL_CHOICES, blank=True, default='')
    # Canonical label, same vocabulary as PromptAnalytics.platform:
    # 'ChatGPT', 'Google Gemini', 'Claude', 'Perplexity', 'Grok', 'DeepSeek'.
    platform = models.CharField(max_length=32)
    run_index = models.PositiveSmallIntegerField(default=1, help_text="1-based; audits run each prompt once")

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='ok')
    is_mention = models.BooleanField(default=False)
    is_cited = models.BooleanField(default=False, help_text="The brand's own site appears in the citations")
    position = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Order in which the brand is named among brands in the answer; null when absent",
    )
    sentiment = models.CharField(max_length=8, choices=SENTIMENT_CHOICES, blank=True, default='')
    competitors_mentioned = models.JSONField(default=list, blank=True, help_text="Competitor names found in the answer")
    rival_positions = models.JSONField(
        default=dict, blank=True,
        help_text="Order each named brand (rivals and you) first appears in the answer, 1 = first",
    )
    cited_domains = models.JSONField(default=list, blank=True, help_text="Hosts of every URL the answer cited, in order")
    response_text = models.TextField(blank=True, default='')
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_prompt_results'
        verbose_name = 'Audit Prompt Result'
        verbose_name_plural = 'Audit Prompt Results'
        ordering = ['audit', 'prompt_index', 'platform', 'run_index']
        indexes = [
            models.Index(fields=['audit', 'prompt_index']),
            models.Index(fields=['audit', 'platform']),
        ]
        unique_together = [('audit', 'prompt_index', 'platform', 'run_index')]

    def __str__(self):
        return f"Audit {self.audit_id} prompt {self.prompt_index} on {self.platform}"


class AuditKeywordResult(models.Model):
    """One discovered keyword's Google ranking — the evidence row behind the SEO half."""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='keyword_results')
    keyword = models.CharField(max_length=255)
    search_volume = models.PositiveIntegerField(null=True, blank=True)
    position = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Organic rank; null when not in the top 100",
    )
    ranking_url = models.URLField(max_length=1000, blank=True, default='')
    outranked_by = models.JSONField(default=list, blank=True, help_text="Hosts ranking above the brand, in order")
    serp_features = models.JSONField(default=list, blank=True, help_text="e.g. ['featured_snippet', 'people_also_ask']")
    # Cross-view: how many engines mention the brand on the prompt matched to
    # this keyword. Null when no prompt matched.
    geo_engines_mentioning = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_keyword_results'
        verbose_name = 'Audit Keyword Result'
        verbose_name_plural = 'Audit Keyword Results'
        ordering = ['audit', '-search_volume']
        indexes = [
            models.Index(fields=['audit']),
        ]
        unique_together = [('audit', 'keyword')]

    def __str__(self):
        return f"Audit {self.audit_id} keyword '{self.keyword}' pos {self.position}"


class AuditPageResult(models.Model):
    """One sampled page from the crawl stage — the evidence behind the Findable pillar."""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='page_results')
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=255, blank=True, default='')
    fetched = models.BooleanField(default=True, help_text="False when the page could not be fetched or parsed")
    error = models.CharField(max_length=200, blank=True, default='')
    word_count = models.PositiveIntegerField(default=0)
    schema_types = models.JSONField(default=list, blank=True, help_text="JSON-LD @type values found on the page")
    author = models.CharField(max_length=120, blank=True, default='', help_text="Byline / author name when one was found")
    external_links = models.PositiveSmallIntegerField(default=0, help_text="Distinct outbound hosts linked from the page")
    last_modified = models.DateField(null=True, blank=True, help_text="dateModified / article:modified_time / datePublished")
    question_headings = models.PositiveSmallIntegerField(default=0)
    has_table = models.BooleanField(default=False)
    has_faq_schema = models.BooleanField(default=False)
    details = models.JSONField(default=dict, blank=True, help_text='Technical / on-page signals: title and description lengths, H1 count, canonical, noindex, viewport, images, internal links, schema gaps, crawl depth, status code')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_page_results'
        verbose_name = 'Audit Page Result'
        verbose_name_plural = 'Audit Page Results'
        ordering = ['audit', 'id']
        indexes = [
            models.Index(fields=['audit']),
        ]
        unique_together = [('audit', 'url')]

    def __str__(self):
        return f"Audit {self.audit_id} page {self.url}"
