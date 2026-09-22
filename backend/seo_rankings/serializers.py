from rest_framework import serializers
from .models import (
    SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory,
    SeoDomainDailyMetrics, SeoKeywordNote, SeoKeywordVolume,
)
from .services.datablue_service import max_tracked_rank


class SeoKeywordRankSerializer(serializers.ModelSerializer):
    """Serializer for SEO keyword ranking data."""
    keyword_text = serializers.CharField(source='keyword.keyword', read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    domain_url = serializers.CharField(source='domain.url', read_only=True)
    # How deep the scrape actually looks, so the UI can say ">30" instead of a
    # hardcoded ">100" that never matched the configured depth. Changing
    # DATABLUE_PAGES in .env moves this without a frontend change.
    max_tracked_rank = serializers.SerializerMethodField()

    def get_max_tracked_rank(self, obj):
        return max_tracked_rank()

    class Meta:
        model = SeoKeywordRank
        fields = [
            'id', 'keyword', 'keyword_text', 'domain', 'domain_name', 'domain_url',
            'max_tracked_rank',
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
            'cannibalisation', 'tags', 'favour',
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


# Fields the rankings list never reads. Each is declared in the page's
# TypeScript interface and then never accessed off a list row — the same
# finding, checked the same way, as the three SERP blobs that were dropped
# before.
#
# Verified against mapKeywordForUI in SeoRankings.tsx, the only place a list
# row is turned into something the table renders. It reads 26 fields; the
# endpoint was sending 44. `kw.keyword` does appear in that file, but on the
# MAPPED object, where it holds keyword_text — not this serializer's `keyword`,
# which is the foreign key id. `target_url` carries its own note in the page:
# "unset on all 3,140 rows".
#
# Measured on domain 157 (2,428 keywords), 200 rows sampled:
#   44 fields -> 1,114 B per row -> 2,641 KB for the page
#   26 fields ->   640 B per row -> 1,517 KB      (-43%)
#
# Anything needing these should call the keyword detail endpoint, which still
# uses the full serializer.
_LIST_UNUSED_FIELDS = (
    'snippets_details', 'keyword_snippet', 'cannibalisation',
    'keyword', 'domain', 'domain_name',
    'max_tracked_rank', 'rank_since_start',
    'month_val', 'month_mark', 'status_from_start',
    'review', 'total_rating', 'total_review',
    'target_url', 'search_results',
    'geo_target', 'geo_target_uule',
    'auto_refresh_count',
    'created_at', 'modified_at',
)


class SeoKeywordRankListSerializer(SeoKeywordRankSerializer):
    """The rankings list, trimmed to what the page actually renders.

    See _LIST_UNUSED_FIELDS above for what is dropped and why.
    """

    class Meta(SeoKeywordRankSerializer.Meta):
        fields = [
            f for f in SeoKeywordRankSerializer.Meta.fields
            if f not in _LIST_UNUSED_FIELDS
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
            'desktop_count', 'mobile_count',
            'rating_0_2', 'rating_2_4', 'rating_4_5',
            'ads_you_above_below', 'ads_you_above', 'ads_you_below',
            'ads_others_above_below', 'ads_others_above', 'ads_others_below',
            'total_keywords',
            'snapshot_date', 'created_at', 'modified_at',
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class SeoKeywordNoteSerializer(serializers.ModelSerializer):
    """Serializer for keyword notes."""
    created_by_name = serializers.CharField(
        source='created_by.first_name', read_only=True
    )

    class Meta:
        model = SeoKeywordNote
        fields = [
            'id', 'seo_keyword_rank', 'domain', 'created_by', 'created_by_name',
            'title', 'notes', 'note_date',
            'created_at', 'modified_at',
        ]
        read_only_fields = ['id', 'created_by', 'domain', 'created_at', 'modified_at']


class SeoKeywordNoteCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating keyword notes."""
    title = serializers.CharField(max_length=100)
    notes = serializers.CharField()
    note_date = serializers.DateField()


class SeoKeywordVolumeSerializer(serializers.ModelSerializer):
    """Serializer for keyword volume history."""

    class Meta:
        model = SeoKeywordVolume
        fields = [
            'id', 'seo_keyword_rank',
            'average_volume', 'top_volume', 'low_volume',
            'comp_level', 'comp_index',
            'month_wise_volume', 'month_labels',
            'status', 'created_at', 'modified_at',
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
