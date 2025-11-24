from rest_framework import serializers
from shared_models.models import (
    Domain, Keyword, PromptGroup, Prompt, PromptAnalytics,
    Competitor, CompetitorPromptAnalytics, CompetitorAnalytics, ShareOfVoiceAnalytics
)
from .models import GeneratedContent


class DomainSerializer(serializers.ModelSerializer):
    """
    Serializer for Domain model
    """
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    keywords_count = serializers.SerializerMethodField()
    prompt_groups_count = serializers.SerializerMethodField()
    prompts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Domain
        fields = [
            'id', 'name', 'url', 'organisation', 'organisation_name',
            'total_mentions', 'total_citations', 'visibility_score', 'average_position',
            'active_alerts', 'sentiment_category', 'sentiment_score',
            'processing_status', 'track_message', 'tracked_at',
            'keywords_count', 'prompt_groups_count', 'prompts_count',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
    
    def get_keywords_count(self, obj):
        return obj.keywords.count()
    
    def get_prompt_groups_count(self, obj):
        return obj.prompt_groups.count()
    
    def get_prompts_count(self, obj):
        return obj.prompts.count()


class KeywordSerializer(serializers.ModelSerializer):
    """
    Serializer for Keyword model
    """
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    
    class Meta:
        model = Keyword
        fields = ['id', 'keyword', 'domain', 'domain_name', 'created_at', 'modified_at']
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for PromptGroup model
    """
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    prompts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PromptGroup
        fields = [
            'id', 'group_id', 'domain', 'domain_name',
            'total_mentions', 'total_citations', 'average_position',
            'prompts_count', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
    
    def get_prompts_count(self, obj):
        return obj.prompts.count()


class PromptSerializer(serializers.ModelSerializer):
    """
    Serializer for Prompt model
    """
    domain_name = serializers.CharField(source='group.domain.name', read_only=True)
    group_id = serializers.CharField(source='group.group_id', read_only=True)
    
    class Meta:
        model = Prompt
        fields = [
            'id', 'prompt', 'group', 'group_id', 'domain_name',
            'track_status', 'type', 'tracked_at', 'track_message',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class PromptAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for PromptAnalytics model
    """
    domain_name = serializers.CharField(source='prompt.group.domain.name', read_only=True)
    prompt_text = serializers.CharField(source='prompt.prompt', read_only=True)
    
    class Meta:
        model = PromptAnalytics
        fields = [
            'id', 'prompt', 'prompt_text', 'domain_name',
            'platform', 'is_mention', 'total_mentions', 'total_citations', 'position',
            'sentiment_category', 'sentiment_score', 'context_summary', 'citation_list',
            'views', 'shares', 'engagement_score', 'competitor_mention_list',
            'topic_list', 'position_history_list', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class ProcessingStatusSerializer(serializers.Serializer):
    """
    Serializer for processing status
    """
    active_threads = serializers.IntegerField()
    max_concurrent = serializers.IntegerField()
    available_slots = serializers.IntegerField()
    active_domain_ids = serializers.ListField(child=serializers.IntegerField())
    domain_counts = serializers.DictField()


class DomainProcessingRequestSerializer(serializers.Serializer):
    """
    Serializer for domain processing requests
    """
    domain_id = serializers.IntegerField(required=True)
    
    def validate_domain_id(self, value):
        try:
            Domain.objects.get(id=value)
        except Domain.DoesNotExist:
            raise serializers.ValidationError("Domain with this ID does not exist")
        return value


class CompetitorSerializer(serializers.ModelSerializer):
    """
    Serializer for Competitor model
    """
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    
    class Meta:
        model = Competitor
        fields = [
            'id', 'domain', 'domain_name', 'name', 'url', 
            'track_status', 'track_message', 'tracked_at',
            'total_mentions', 'visibility_score', 'sentiment_score', 'average_position',
            'share_of_voice_percentage', 'trend_percentage', 
            'created_by', 'created_at', 'modified_at'
        ]
        read_only_fields = [
            'id', 'track_status', 'track_message', 'tracked_at',
            'total_mentions', 'visibility_score', 'sentiment_score', 'average_position',
            'share_of_voice_percentage', 'trend_percentage',
            'created_at', 'modified_at'
        ]


class CompetitorPromptAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for CompetitorPromptAnalytics model
    """
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


class CompetitorAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for CompetitorAnalytics model
    """
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = CompetitorAnalytics
        fields = [
            'id', 'competitor', 'competitor_name', 'platform', 'total_mentions',
            'position', 'sentiment_score', 'timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ShareOfVoiceAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for ShareOfVoiceAnalytics model
    """
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    competitor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ShareOfVoiceAnalytics
        fields = [
            'id', 'domain', 'domain_name', 'competitor', 'competitor_name',
            'platform', 'share_percentage', 'mention_count', 'market_position',
            'timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_competitor_name(self, obj):
        if obj.competitor:
            return obj.competitor.name
        return f"{obj.domain.name} (Your Brand)"


class GeneratedContentSerializer(serializers.ModelSerializer):
    """
    Serializer for GeneratedContent model
    """
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = GeneratedContent
        fields = [
            'id', 'domain', 'domain_name', 'title', 'content_html', 'content_json',
            'source_type', 'source_id', 'source_reference',
            'article_type', 'keywords', 'tone', 'style', 'goal', 'audience', 'depth',
            'word_count', 'actual_word_count',
            'status', 'scheduled_date', 'published_date', 'priority',
            'model_used', 'generation_time_seconds', 'prompt_tokens', 'completion_tokens',
            'created_at', 'modified_at'
        ]
        read_only_fields = [
            'id', 'actual_word_count', 'model_used',
            'generation_time_seconds', 'prompt_tokens', 'completion_tokens',
            'created_at', 'modified_at'
        ]


class ContentGenerationRequestSerializer(serializers.Serializer):
    """
    Serializer for content generation requests
    """
    domain_id = serializers.IntegerField(required=True)
    title = serializers.CharField(required=True, max_length=500)
    keywords = serializers.CharField(required=True)
    article_type = serializers.ChoiceField(
        choices=['blog', 'guide', 'comparison', 'listicle', 'technical'],
        default='blog'
    )
    tone = serializers.CharField(default='professional')
    style = serializers.CharField(default='informative')
    goal = serializers.CharField(default='educate')
    audience = serializers.CharField(default='general')
    depth = serializers.CharField(default='comprehensive')
    word_count = serializers.IntegerField(default=1500)
    source_type = serializers.ChoiceField(
        choices=['topic', 'content_gap', 'manual'],
        default='manual'
    )
    source_id = serializers.IntegerField(required=False, allow_null=True)
    source_reference = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.CharField(default='medium')
    scheduled_date = serializers.DateTimeField(required=False, allow_null=True)

    def validate_domain_id(self, value):
        try:
            Domain.objects.get(id=value)
        except Domain.DoesNotExist:
            raise serializers.ValidationError("Domain with this ID does not exist")
        return value
