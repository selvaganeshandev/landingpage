from rest_framework import serializers
from .models import GeneratedContent
from domains.models import Domain


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


