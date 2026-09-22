from django.conf import settings
from rest_framework import serializers

from .models import Audit, AuditKeywordResult, AuditPageResult, AuditPromptResult


class AuditPromptResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditPromptResult
        fields = [
            'id', 'prompt_index', 'prompt_text', 'topic', 'funnel_stage', 'platform', 'run_index',
            'status', 'is_mention', 'is_cited', 'position', 'sentiment', 'competitors_mentioned',
            'rival_positions', 'cited_domains', 'response_text', 'latency_ms', 'error', 'created_at',
        ]


class AuditKeywordResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditKeywordResult
        fields = [
            'id', 'keyword', 'search_volume', 'position', 'ranking_url', 'outranked_by',
            'serp_features', 'geo_engines_mentioning', 'created_at',
        ]


class AuditPageResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditPageResult
        fields = [
            'id', 'url', 'title', 'fetched', 'error', 'word_count', 'schema_types', 'author',
            'external_links', 'last_modified', 'question_headings', 'has_table', 'has_faq_schema', 'details', 'created_at',
        ]


class _ProgressMixin(serializers.Serializer):
    stage_index = serializers.IntegerField(read_only=True)
    stage_total = serializers.SerializerMethodField()
    stage_label = serializers.SerializerMethodField()
    is_claimed = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    def get_stage_total(self, obj):
        return len(Audit.STAGE_ORDER)

    def get_stage_label(self, obj):
        return dict(Audit.STAGE_CHOICES).get(obj.stage, '')


class PublicAuditSerializer(_ProgressMixin, serializers.ModelSerializer):
    """What an anonymous visitor holding the token may see.

    No requester email / IP, no internal config. The report body is attached
    only once the audit is DONE; before that the visitor gets stage progress.
    A failed audit shows a generic message, never the raw exception.
    """
    error = serializers.SerializerMethodField()
    report = serializers.SerializerMethodField()
    seo_enabled = serializers.SerializerMethodField()
    landing_url = serializers.SerializerMethodField()
    live = serializers.SerializerMethodField()

    LIVE_ROWS = 8

    class Meta:
        model = Audit
        fields = [
            'public_token', 'host', 'website', 'country', 'brand_name', 'industry', 'seo_enabled',
            'landing_url',
            'competitors', 'tech_stack',
            'status', 'stage', 'stage_index', 'stage_total', 'stage_label', 'progress', 'stage_detail',
            'live',
            'error',
            'geo_score', 'geo_stage', 'appearances', 'cited_runs', 'total_runs',
            'engines_preferred', 'engines_total', 'share_of_voice',
            'seo_visibility', 'keywords_top10', 'keywords_total',
            'report', 'opens', 'is_claimed', 'is_expired', 'expires_at',
            'created_at', 'completed_at',
        ]
        read_only_fields = fields

    def get_seo_enabled(self, obj):
        """Whether this audit ranks keywords on Google.

        Derived, not the config blob: the progress strip has to label the SERP
        stage either as a real step or as skipped, and guessing wrong tells the
        visitor a stage was skipped while they watch it run.
        """
        return bool((obj.config or {}).get('seo_enabled'))

    def get_landing_url(self, obj):
        """Where to send this visitor back to, or '' for no back link.

        Only for audits that came from the landing page: those visitors have no
        account and nothing else to reach here, so the report is the end of the
        road. An audit an admin started by hand has no 'back' to offer.
        """
        if obj.source != 'landing':
            return ''
        return getattr(settings, 'AUDIT_LANDING_URL', '') or ''

    def get_error(self, obj):
        if obj.status != 'FAIL':
            return ''
        return 'This audit could not be completed. Please try again later.'

    def get_live(self, obj):
        """The newest engine answers while the audit runs — the landing page's
        "watch it run" feed. Empty once it is DONE or FAIL: the report carries
        the full evidence, and a finished feed would just be a stale replay.
        No response text; only what the feed row shows.
        """
        if obj.status not in ('INIT', 'PROC'):
            return []
        from .models import AuditPromptResult
        rows = (
            AuditPromptResult.objects.filter(audit=obj, status='ok')
            .order_by('-created_at', '-id')[:self.LIVE_ROWS]
            .values('platform', 'prompt_text', 'is_mention', 'is_cited', 'position', 'competitors_mentioned', 'cited_domains', 'created_at')
        )
        out = []
        for r in rows:
            rivals = r.get('competitors_mentioned') or []
            cited = [h for h in (r.get('cited_domains') or []) if h and obj.host not in h]
            out.append({
                'engine': r['platform'],
                'prompt': r['prompt_text'],
                'result': 'cited' if r['is_cited'] else 'mentioned' if r['is_mention'] else 'absent',
                'position': int(r['position']) if r['position'] is not None else None,
                'instead': rivals[0] if rivals else (cited[0] if cited else ''),
                'at': r['created_at'].isoformat() if r.get('created_at') else '',
            })
        return out

    def get_report(self, obj):
        return obj.report if obj.status == 'DONE' else None


class AuditListSerializer(_ProgressMixin, serializers.ModelSerializer):
    """One row of the leads table."""
    requested_by_email = serializers.SerializerMethodField()
    claimed_domain_name = serializers.SerializerMethodField()

    class Meta:
        model = Audit
        fields = [
            'id', 'public_token', 'host', 'website', 'country', 'source',
            'brand_name', 'industry', 'competitors',
            'status', 'stage', 'stage_index', 'stage_total', 'stage_label', 'progress', 'error',
            'geo_score', 'geo_stage', 'seo_visibility', 'engines_preferred', 'engines_total',
            'opens', 'last_opened_at', 'expires_at', 'is_expired',
            'emailed_at', 'emailed_to', 'email_count',
            'is_claimed', 'claimed_at', 'claimed_domain', 'claimed_domain_name',
            'requested_by', 'requested_by_email', 'requester_email',
            'created_at', 'completed_at',
        ]
        read_only_fields = fields

    def get_requested_by_email(self, obj):
        return getattr(obj.requested_by, 'email', '') if obj.requested_by_id else ''

    def get_claimed_domain_name(self, obj):
        return getattr(obj.claimed_domain, 'name', '') if obj.claimed_domain_id else ''


class AuditDetailSerializer(AuditListSerializer):
    """The leads row plus everything the engine stored."""
    prompt_results = AuditPromptResultSerializer(many=True, read_only=True)
    keyword_results = AuditKeywordResultSerializer(many=True, read_only=True)
    page_results = AuditPageResultSerializer(many=True, read_only=True)

    class Meta(AuditListSerializer.Meta):
        fields = AuditListSerializer.Meta.fields + [
            'tech_stack', 'config', 'stage_detail', 'grounding', 'report',
            'appearances', 'cited_runs', 'total_runs', 'share_of_voice',
            'keywords_top10', 'keywords_total', 'requester_ip',
            'prompt_results', 'keyword_results', 'page_results',
        ]
        read_only_fields = fields


class AuditCreateSerializer(serializers.Serializer):
    url = serializers.CharField(max_length=2048)
    country = serializers.CharField(max_length=2, required=False, default='us')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    # What the visitor calls the brand. The profile stage keeps it when set,
    # so mention detection looks for the name they use, not the one the
    # model guesses from the homepage.
    brand_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    force = serializers.BooleanField(required=False, default=False)
