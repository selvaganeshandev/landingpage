from rest_framework import serializers
from .models import SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory, SeoDomainDailyMetrics


class SeoKeywordRankSerializer(serializers.ModelSerializer):
    """Serializer for SEO keyword ranking data."""
    keyword_text = serializers.CharField(source='keyword.keyword', read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    domain_url = serializers.CharField(source='domain.url', read_only=True)

    class Meta:
        model = SeoKeywordRank
        fields = [
            'id', 'keyword', 'keyword_text', 'domain', 'domain_name', 'domain_url',
            'platform', 'rank_now', 'top_rank', 'rank_since_start',
            'day_val', 'day_mark', 'week_val', 'week_mark',
            'half_month_val', 'half_month_mark', 'month_val', 'month_mark',
            'status_from_start',
            'featured_snippet', 'knowledge_panel', 'ads', 'review',
            'total_rating', 'total_review',
            'snippets_details', 'keyword_snippet',
            'gsc_clicks', 'gsc_impressions',
            'site_url', 'target_url', 'search_results', 'search_volume',
            'region', 'isocode', 'language_code', 'geo_target', 'geo_target_uule',
            'auto_call_status', 'auto_refresh_count', 'last_ranked_date',
            'cannibalisation',
            'created_at', 'modified_at',
        ]
        read_only_fields = [
            'id', 'rank_now', 'top_rank',
            'day_val', 'day_mark', 'week_val', 'week_mark',
            'half_month_val', 'half_month_mark', 'month_val', 'month_mark',
            'status_from_start',
            'featured_snippet', 'knowledge_panel', 'ads', 'review',
            'total_rating', 'total_review',
            'snippets_details', 'keyword_snippet',
            'site_url', 'search_results',
            'auto_call_status', 'auto_refresh_count', 'last_ranked_date',
            'cannibalisation',
            'created_at', 'modified_at',
        ]


class SeoKeywordRankCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/adding keywords to SEO tracking."""

    class Meta:
        model = SeoKeywordRank
        fields = [
            'keyword', 'domain', 'platform',
            'target_url', 'region', 'isocode', 'language_code',
            'geo_target', 'geo_target_uule',
        ]


class SeoRankHistorySerializer(serializers.ModelSerializer):
    """Serializer for daily rank history."""

    class Meta:
        model = SeoRankHistory
        fields = ['id', 'seo_keyword_rank', 'rank_position', 'snapshot_date', 'created_at']
        read_only_fields = ['id', 'created_at']


class SeoSerpFeatureHistorySerializer(serializers.ModelSerializer):
    """Serializer for SERP feature history."""

    class Meta:
        model = SeoSerpFeatureHistory
        fields = [
            'id', 'seo_keyword_rank',
            'featured_snippet_url_list', 'featured_snippet_history',
            'ad_snippet_url_list', 'ad_snippet_history',
            'url_status', 'other_history', 'comp_today',
            'created_at', 'modified_at',
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class SeoDomainDailyMetricsSerializer(serializers.ModelSerializer):
    """Serializer for domain-level daily SEO metrics."""
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = SeoDomainDailyMetrics
        fields = [
            'id', 'domain', 'domain_name',
            'score_meter', 'top_score',
            'improved_count', 'declined_count', 'no_change_count', 'activity_level',
            'top_1_count', 'top_3_count', 'top_10_count',
            'top_50_count', 'top_100_count', 'not_ranked_count',
            'desktop_count', 'mobile_count', 'total_keywords',
            'snapshot_date', 'created_at', 'modified_at',
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
