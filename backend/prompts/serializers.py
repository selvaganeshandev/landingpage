from rest_framework import serializers
from .models import PromptCluster, Prompt, PromptAnalytics


class PromptClusterSerializer(serializers.ModelSerializer):
    """Serializer for PromptCluster model"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    
    class Meta:
        model = PromptCluster
        fields = [
            'id', 'cluster_id', 'domain', 'domain_name', 
            'organisation', 'organisation_name',
            'total_mentions', 'total_citations', 'visibility_score', 
            'average_position', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptSerializer(serializers.ModelSerializer):
    """Serializer for Prompt model"""
    cluster_id = serializers.CharField(source='cluster.cluster_id', read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    
    class Meta:
        model = Prompt
        fields = [
            'id', 'prompt', 'cluster', 'cluster_id', 'domain', 'domain_name',
            'organisation', 'organisation_name', 'track_status', 'type',
            'total_mentions', 'total_citations', 'visibility_score', 
            'average_position', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for PromptAnalytics model"""
    prompt_text = serializers.CharField(source='prompt.prompt', read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    
    class Meta:
        model = PromptAnalytics
        fields = [
            'id', 'prompt', 'prompt_text', 'domain', 'domain_name',
            'organisation', 'organisation_name', 'platform', 'is_mention',
            'total_mentions', 'total_citations', 'position', 
            'sentiment', 'sentiment_score', 'context_summary', 'citations',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptClusterDetailSerializer(PromptClusterSerializer):
    """Detailed serializer for PromptCluster with related prompts"""
    prompts = PromptSerializer(many=True, read_only=True)
    
    class Meta(PromptClusterSerializer.Meta):
        fields = PromptClusterSerializer.Meta.fields + ['prompts']


class PromptDetailSerializer(PromptSerializer):
    """Detailed serializer for Prompt with related analytics"""
    analytics = PromptAnalyticsSerializer(many=True, read_only=True)
    
    class Meta(PromptSerializer.Meta):
        fields = PromptSerializer.Meta.fields + ['analytics']
