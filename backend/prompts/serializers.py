from rest_framework import serializers
from .models import PromptGroup, Prompt, PromptAnalytics


class PromptGroupSerializer(serializers.ModelSerializer):
    """Serializer for PromptGroup model"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    
    class Meta:
        model = PromptGroup
        fields = [
            'id', 'group_id', 'domain', 'domain_name', 
            'total_mentions', 'total_citations', 
            'average_position', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptSerializer(serializers.ModelSerializer):
    """Serializer for Prompt model"""
    group_id = serializers.CharField(source='group.group_id', read_only=True)
    domain_name = serializers.CharField(source='group.domain.name', read_only=True)
    
    class Meta:
        model = Prompt
        fields = [
            'id', 'prompt', 'group', 'group_id', 'domain_name',
            'track_status', 'type',
            'tracked_at', 'track_message', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for PromptAnalytics model"""
    prompt_text = serializers.CharField(source='prompt.prompt', read_only=True)
    domain_name = serializers.CharField(source='prompt.group.domain.name', read_only=True)
    group_id = serializers.CharField(source='prompt.group.group_id', read_only=True)
    
    class Meta:
        model = PromptAnalytics
        fields = [
            'id', 'prompt', 'prompt_text', 'group_id', 'domain_name',
            'platform', 'is_mention',
            'total_mentions', 'total_citations', 'position', 
            'sentiment_category', 'sentiment_score', 'context_summary', 'citation_list',
            'views', 'shares', 'engagement_score', 'competitor_mention_list',
            'topic_list', 'position_history_list', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptGroupDetailSerializer(PromptGroupSerializer):
    """Detailed serializer for PromptGroup with related prompts"""
    prompts = PromptSerializer(many=True, read_only=True)
    
    class Meta(PromptGroupSerializer.Meta):
        fields = PromptGroupSerializer.Meta.fields + ['prompts']


class PromptDetailSerializer(PromptSerializer):
    """Detailed serializer for Prompt with related analytics"""
    analytics = PromptAnalyticsSerializer(many=True, read_only=True)
    
    class Meta(PromptSerializer.Meta):
        fields = PromptSerializer.Meta.fields + ['analytics']
