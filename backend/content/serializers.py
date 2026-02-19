from rest_framework import serializers
from .models import GeneratedContent, CMSProvider, ScheduledPublication, ContentComment
from domains.models import Domain


class GeneratedContentSerializer(serializers.ModelSerializer):
    """
    Serializer for GeneratedContent model
    """
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    total_comments = serializers.IntegerField(read_only=True, default=0)
    pending_comments = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = GeneratedContent
        fields = [
            'id', 'domain', 'domain_name', 'title', 'content_html', 'content_json',
            'source_type', 'source_id', 'source_reference',
            'article_type', 'keywords', 'tone', 'style', 'goal', 'audience', 'depth',
            'word_count', 'actual_word_count',
            'status', 'scheduled_date', 'published_date', 'priority',
            'model_used', 'generation_time_seconds', 'prompt_tokens', 'completion_tokens',
            'ai_detection_score', 'human_detection_score', 'ai_detection_label', 'ai_detection_checked_at',
            'humanise_status', 'pre_humanise_content', 'humanise_started_at',
            'humanise_completed_at', 'humanise_error',
            'total_comments', 'pending_comments',
            'created_at', 'modified_at'
        ]
        read_only_fields = [
            'id', 'actual_word_count', 'model_used',
            'generation_time_seconds', 'prompt_tokens', 'completion_tokens',
            'humanise_status', 'pre_humanise_content',
            'humanise_started_at', 'humanise_completed_at', 'humanise_error',
            'total_comments', 'pending_comments',
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
        choices=[
            # Article Types
            'blog', 'guide', 'comparison', 'listicle', 'technical',
            # Web Page Content Types
            'landing_page', 'services_page', 'product_page', 'features_page', 'resource_page',
            # Social Media Types
            'twitter_post', 'linkedin_post', 'facebook_post', 'instagram_caption', 'social_thread',
            # Community Post Types
            'reddit_post', 'quora_answer', 'forum_post', 'product_hunt', 'newsletter_snippet',
        ],
        default='blog'
    )
    target_country = serializers.CharField(default='united_states')
    target_language = serializers.CharField(default='us_english')
    references = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    tone = serializers.CharField(default='professional', allow_blank=True)
    style = serializers.CharField(default='informative', allow_blank=True)
    goal = serializers.CharField(default='educate')
    audience = serializers.CharField(default='general')
    depth = serializers.CharField(default='comprehensive')
    word_count = serializers.IntegerField(default=1500)
    source_type = serializers.ChoiceField(
        choices=['topic', 'content_gap', 'answer_gap', 'manual'],
        default='manual'
    )
    source_id = serializers.IntegerField(required=False, allow_null=True)
    source_reference = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.CharField(default='medium')
    scheduled_date = serializers.DateTimeField(required=False, allow_null=True)
    # Domain content guidelines (optional context for AI)
    key_messages = serializers.CharField(required=False, allow_blank=True, default='')
    topics_to_avoid = serializers.CharField(required=False, allow_blank=True, default='')
    additional_instructions = serializers.CharField(required=False, allow_blank=True, default='')
    brand_values = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_domain_id(self, value):
        try:
            Domain.objects.get(id=value)
        except Domain.DoesNotExist:
            raise serializers.ValidationError("Domain with this ID does not exist")
        return value


class CMSProviderSerializer(serializers.ModelSerializer):
    """
    Serializer for CMSProvider model
    """
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    
    class Meta:
        model = CMSProvider
        fields = [
            'id', 'domain', 'domain_name', 'provider_type', 'name',
            'settings', 'is_active', 'is_default',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
    
    def validate(self, data):
        """Ensure only one default per domain"""
        if data.get('is_default'):
            domain = data.get('domain')
            provider_id = self.instance.id if self.instance else None
            existing_default = CMSProvider.objects.filter(
                domain=domain,
                is_default=True
            ).exclude(id=provider_id).exists()
            
            if existing_default:
                raise serializers.ValidationError({
                    'is_default': 'Only one CMS provider can be set as default per domain'
                })
        return data


class CMSProviderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating CMSProvider with WordPress-specific validation
    """
    class Meta:
        model = CMSProvider
        fields = [
            'domain', 'provider_type', 'name', 'settings',
            'is_active', 'is_default'
        ]
    
    def validate_settings(self, value):
        """Validate WordPress settings structure"""
        provider_type = self.initial_data.get('provider_type', 'wordpress')
        
        if provider_type == 'wordpress':
            required_fields = ['api_url', 'username', 'app_password']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"WordPress settings must include '{field}'"
                    )
            
            # Validate API URL format
            api_url = value.get('api_url', '')
            if not api_url.startswith('http'):
                raise serializers.ValidationError(
                    "API URL must be a valid HTTP/HTTPS URL"
                )
        
        if provider_type == 'strapi':
            required_fields = ['api_url', 'token']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Strapi settings must include '{field}'"
                    )
            api_url = value.get('api_url', '')
            if not api_url.startswith('http'):
                raise serializers.ValidationError(
                    "API URL must be a valid HTTP/HTTPS URL"
                )
            # Optional: collection endpoint default
            if 'collection' not in value:
                value['collection'] = '/api/articles'

        if provider_type == 'joomla':
            required_fields = ['api_url', 'token', 'catid']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Joomla settings must include '{field}'"
                    )
            api_url = value.get('api_url', '')
            if not api_url.startswith('http'):
                raise serializers.ValidationError(
                    "API URL must be a valid HTTP/HTTPS URL"
                )
            if 'endpoint' not in value:
                value['endpoint'] = '/api/index.php/v1/content/articles'
            if 'state' not in value:
                value['state'] = 1  # published by default

        if provider_type == 'drupal':
            required_fields = ['api_url', 'username', 'password', 'content_type']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Drupal settings must include '{field}'"
                    )
            api_url = value.get('api_url', '')
            if not api_url.startswith('http'):
                raise serializers.ValidationError(
                    "API URL must be a valid HTTP/HTTPS URL"
                )
            if 'endpoint' not in value:
                value['endpoint'] = '/entity/node?_format=json'
            if 'body_format' not in value:
                value['body_format'] = 'basic_html'
            if 'status' not in value:
                value['status'] = 1  # published by default

        if provider_type == 'contentful':
            required_fields = ['api_url', 'management_token', 'space_id', 'environment_id', 'content_type_id']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Contentful settings must include '{field}'"
                    )
            api_url = value.get('api_url', '')
            if not api_url.startswith('http'):
                raise serializers.ValidationError(
                    "API URL must be a valid HTTP/HTTPS URL"
                )
            # Sensible defaults
            if 'environment_id' not in value or not value.get('environment_id'):
                value['environment_id'] = 'master'
            if 'api_url' not in value or not value.get('api_url'):
                value['api_url'] = 'https://api.contentful.com'

        # Generic validation for other providers: at least api_url
        if provider_type not in ['wordpress', 'strapi', 'joomla', 'drupal', 'contentful']:
            if 'api_url' not in value or not value.get('api_url', '').startswith('http'):
                raise serializers.ValidationError(
                    "API URL must be provided and be a valid HTTP/HTTPS URL"
                )
        
        return value


class ScheduledPublicationSerializer(serializers.ModelSerializer):
    """
    Serializer for ScheduledPublication model
    """
    content_title = serializers.CharField(source='content.title', read_only=True)
    cms_provider_name = serializers.CharField(source='cms_provider.name', read_only=True)
    
    class Meta:
        model = ScheduledPublication
        fields = [
            'id', 'content', 'content_title', 'cms_provider', 'cms_provider_name',
            'scheduled_at', 'status', 'wordpress_post_id', 'wordpress_url',
            'error_message', 'published_at', 'created_at', 'modified_at'
        ]
        read_only_fields = [
            'id', 'status', 'wordpress_post_id', 'wordpress_url',
            'error_message', 'published_at', 'created_at', 'modified_at'
        ]


class PublishContentSerializer(serializers.Serializer):
    """
    Serializer for publishing content
    """
    content_id = serializers.IntegerField(required=True)
    cms_provider_id = serializers.IntegerField(required=True)
    publish_now = serializers.BooleanField(default=False)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validate publish options"""
        publish_now = data.get('publish_now', False)
        scheduled_at = data.get('scheduled_at')
        
        if not publish_now and not scheduled_at:
            raise serializers.ValidationError(
                "Either 'publish_now' must be True or 'scheduled_at' must be provided"
            )
        
        if publish_now and scheduled_at:
            raise serializers.ValidationError(
                "Cannot set both 'publish_now' and 'scheduled_at'"
            )

        return data


class ContentCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for ContentComment model (Google Docs-style comments)
    """
    author_name = serializers.SerializerMethodField()
    author_email = serializers.CharField(source='author.email', read_only=True)
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ContentComment
        fields = [
            'id', 'content', 'author', 'author_name', 'author_email',
            'selected_text', 'comment', 'suggestion', 'status',
            'resolved_by', 'resolved_by_name', 'resolved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'author', 'resolved_by', 'resolved_at',
            'created_at', 'updated_at'
        ]

    def get_author_name(self, obj):
        if obj.author.first_name:
            return f"{obj.author.first_name} {obj.author.last_name or ''}".strip()
        return obj.author.email

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            if obj.resolved_by.first_name:
                return f"{obj.resolved_by.first_name} {obj.resolved_by.last_name or ''}".strip()
            return obj.resolved_by.email
        return None


class CreateContentCommentSerializer(serializers.Serializer):
    """
    Serializer for creating a new content comment
    """
    selected_text = serializers.CharField(required=True)
    comment = serializers.CharField(required=True)
    suggestion = serializers.CharField(required=False, allow_blank=True, default='')


