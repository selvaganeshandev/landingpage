from rest_framework import serializers
from .models import Competitor, CompetitorAnalytics, CompetitorPrompt


class CompetitorSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Competitor
        fields = [
            'id', 'domain', 'domain_name', 'name', 'url', 'total_mentions',
            'visibility_score', 'sentiment_score', 'average_position',
            'share_of_voice_percentage', 'trend_percentage', 'created_by',
            'created_by_email', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


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
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = CompetitorPrompt
        fields = [
            'id', 'competitor', 'competitor_name', 'prompt_text', 'total_mentions',
            'position', 'your_mentions', 'platform_list', 'created_by',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']

