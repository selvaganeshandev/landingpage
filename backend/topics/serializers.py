from rest_framework import serializers
from .models import Topic, TopicAnalytics, TopicPrompt


class TopicSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Topic
        fields = [
            'id', 'domain', 'domain_name', 'name', 'keyword_list', 'total_mentions',
            'visibility_score', 'sentiment_score', 'trend_percentage', 'platform_list',
            'created_by', 'created_by_email', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class TopicAnalyticsSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    
    class Meta:
        model = TopicAnalytics
        fields = [
            'id', 'topic', 'topic_name', 'total_mentions', 'visibility_score',
            'sentiment_score', 'timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TopicPromptSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    
    class Meta:
        model = TopicPrompt
        fields = [
            'id', 'topic', 'topic_name', 'prompt_text', 'relevance_score',
            'search_volume', 'platform_list', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

