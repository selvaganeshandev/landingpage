"""
Serializers for Misinformation Module
"""
from rest_framework import serializers
from .models import (
    MisinformationScan,
    CitationURL,
    CitationContent,
    MisinformationAlert,
    MisinformationAnalytics,
)


class CitationContentSerializer(serializers.ModelSerializer):
    """Serializer for citation content."""

    class Meta:
        model = CitationContent
        fields = [
            'id',
            'extracted_text',
            'page_title',
            'meta_description',
            'publish_date',
            'crawled_at',
        ]


class CitationURLSerializer(serializers.ModelSerializer):
    """Serializer for citation URLs."""
    content = CitationContentSerializer(read_only=True)

    class Meta:
        model = CitationURL
        fields = [
            'id',
            'url',
            'is_crawlable',
            'crawl_status',
            'crawl_error',
            'http_status_code',
            'last_crawled_at',
            'created_at',
            'content',
        ]


class MisinformationAlertListSerializer(serializers.ModelSerializer):
    """Serializer for listing misinformation alerts."""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    prompt_text = serializers.CharField(source='prompt.prompt', read_only=True)
    citation_url_display = serializers.CharField(source='citation_url.url', read_only=True)

    class Meta:
        model = MisinformationAlert
        fields = [
            'id',
            'domain_name',
            'prompt_text',
            'citation_url_display',
            'alert_type',
            'severity',
            'llm_claim',
            'explanation',
            'status',
            'created_at',
        ]


class MisinformationAlertDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed misinformation alert view."""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    domain_url = serializers.URLField(source='domain.url', read_only=True)
    prompt_text = serializers.CharField(source='prompt.prompt', read_only=True)
    citation_url = CitationURLSerializer(read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = MisinformationAlert
        fields = [
            'id',
            'domain_name',
            'domain_url',
            'prompt_text',
            'prompt_analytics_id',
            'citation_url',
            'alert_type',
            'severity',
            'llm_claim',
            'source_content',
            'explanation',
            'status',
            'reviewed_by_email',
            'reviewed_at',
            'created_at',
            'modified_at',
        ]


class MisinformationAlertUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating misinformation alert status."""

    class Meta:
        model = MisinformationAlert
        fields = ['status']

    def validate_status(self, value):
        allowed_statuses = ['reviewed', 'resolved', 'dismissed']
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(allowed_statuses)}"
            )
        return value


class MisinformationScanSerializer(serializers.ModelSerializer):
    """Serializer for misinformation scans."""
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = MisinformationScan
        fields = [
            'id',
            'domain_name',
            'status',
            'started_at',
            'completed_at',
            'total_prompts_scanned',
            'total_citations_found',
            'total_alerts_generated',
            'error_message',
            'created_at',
        ]


class MisinformationAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for misinformation analytics."""
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = MisinformationAnalytics
        fields = [
            'id',
            'domain_name',
            'date',
            'total_detected',
            'broken_links_count',
            'misinformation_count',
            'outdated_count',
            'by_severity',
            'created_at',
        ]


class DashboardSerializer(serializers.Serializer):
    """Serializer for dashboard summary data."""
    total_detected = serializers.IntegerField()
    broken_links = serializers.IntegerField()
    misinformation = serializers.IntegerField()
    outdated = serializers.IntegerField()
    by_severity = serializers.DictField()
    recent_alerts = MisinformationAlertListSerializer(many=True)
    trend = serializers.ListField(child=MisinformationAnalyticsSerializer())


class TriggerScanSerializer(serializers.Serializer):
    """Serializer for triggering a manual scan."""
    domain_id = serializers.IntegerField(required=True)
    prompt_analytics_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
