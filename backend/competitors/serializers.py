from rest_framework import serializers
from .models import (
    Competitor,
    CompetitorAnalytics,
    CompetitorPrompt,
    CompetitorPromptAnalytics,
    CompetitorMetricSnapshot,
    CompetitiveInsight,
)


class CompetitorSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Competitor
        fields = [
            'id', 'domain', 'domain_name', 'name', 'url', 
            'track_status', 'track_message', 'tracked_at',
            'total_mentions', 'visibility_score', 'sentiment_score', 'average_position',
            'share_of_voice_percentage', 'trend_percentage', 
            'created_by', 'created_by_email', 'created_at', 'modified_at'
        ]
        read_only_fields = [
            'id', 'track_status', 'track_message', 'tracked_at',
            'total_mentions', 'visibility_score', 'sentiment_score', 'average_position',
            'share_of_voice_percentage', 'trend_percentage',
            'created_at', 'modified_at'
        ]


class CompetitorAnalyticsSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = CompetitorAnalytics
        fields = [
            'id', 'competitor', 'competitor_name', 'platform', 'total_mentions',
            'position', 'sentiment_score', 'timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CompetitorPromptSerializer(serializers.ModelSerializer):
    """DEPRECATED: Use CompetitorPromptAnalyticsSerializer instead"""
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = CompetitorPrompt
        fields = [
            'id', 'competitor', 'competitor_name', 'prompt_text', 'total_mentions',
            'position', 'your_mentions', 'platform_list', 'created_by',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class CompetitorPromptAnalyticsSerializer(serializers.ModelSerializer):
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    prompt_text = serializers.CharField(source='prompt.prompt', read_only=True)
    domain_name = serializers.CharField(source='competitor.domain.name', read_only=True)
    
    class Meta:
        model = CompetitorPromptAnalytics
        fields = [
            'id', 'competitor', 'competitor_name', 'prompt', 'prompt_text', 'domain_name',
            'track_status', 'track_message', 'tracked_at',
            'is_mentioned', 'position', 'mention_count', 
            'sentiment_category', 'sentiment_score',
            'platform', 'response_text', 'citation_list',
            'created_at', 'modified_at'
        ]
        read_only_fields = [
            'id', 'track_status', 'track_message', 'tracked_at',
            'is_mentioned', 'position', 'mention_count', 
            'sentiment_category', 'sentiment_score',
            'platform', 'response_text', 'citation_list',
            'created_at', 'modified_at'
        ]


class CompetitorMetricSnapshotSerializer(serializers.ModelSerializer):
    competitor_name = serializers.SerializerMethodField()
    
    def get_competitor_name(self, obj):
        """Return competitor name, or 'Your Brand' if competitor is None (domain snapshot)"""
        if obj.competitor is None:
            return 'Your Brand'
        return obj.competitor.name if obj.competitor else 'Unknown'

    class Meta:
        model = CompetitorMetricSnapshot
        fields = [
            'id',
            'competitor',
            'competitor_name',
            'domain',
            'timestamp',
            'total_mentions',
            'total_citations',
            'visibility_score',
            'sentiment_score',
            'average_position',
            'share_of_voice_percentage',
            'trend_percentage',
            'track_status',
            'created_at',
        ]
        read_only_fields = fields


class CompetitiveInsightSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='insight_type', read_only=True)

    class Meta:
        model = CompetitiveInsight
        fields = [
            'id',
            'domain',
            'title',
            'description',
            'type',
            'category',
            'impact',
            'snapshot_version',
            'insight_data',
            'model_name',
            'generated_at',
        ]
        read_only_fields = fields

