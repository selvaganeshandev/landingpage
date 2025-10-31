from rest_framework import serializers
from .models import SentimentAnalytics, ShareOfVoiceAnalytics


class SentimentAnalyticsSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    
    class Meta:
        model = SentimentAnalytics
        fields = [
            'id', 'domain', 'domain_name', 'theme', 'positive_percentage',
            'neutral_percentage', 'negative_percentage', 'mention_count',
            'platform', 'timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ShareOfVoiceAnalyticsSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    competitor_name = serializers.CharField(source='competitor.name', read_only=True, allow_null=True)
    brand_name = serializers.SerializerMethodField()
    
    def get_brand_name(self, obj):
        """Return competitor name if exists, otherwise domain name (your brand)."""
        return obj.competitor.name if obj.competitor else obj.domain.name
    
    class Meta:
        model = ShareOfVoiceAnalytics
        fields = [
            'id', 'domain', 'domain_name', 'competitor', 'competitor_name',
            'brand_name', 'platform', 'share_percentage', 'mention_count',
            'market_position', 'timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'brand_name']

