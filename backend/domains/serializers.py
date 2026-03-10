from rest_framework import serializers
from .models import Domain, DomainAccess, InternalLinkMap, ReferenceDocument


class DomainSerializer(serializers.ModelSerializer):
    """Serializer for Domain model"""
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    latest_health_score = serializers.SerializerMethodField()
    latest_health_grade = serializers.SerializerMethodField()
    latest_health_grade_color = serializers.SerializerMethodField()

    class Meta:
        model = Domain
        fields = [
            'id', 'name', 'url', 'short_description',
            'tone_of_voice', 'content_style', 'key_messages', 'topics_to_avoid',
            'target_audience', 'brand_values', 'key_competitors',
            'country', 'niches', 'organisation', 'organisation_name',
            'total_mentions', 'total_citations', 'visibility_score',
            'average_position', 'active_alerts', 'sentiment_category',
            'sentiment_score', 'processing_status', 'track_message', 'tracked_at',
            'created_at', 'modified_at',
            'latest_health_score', 'latest_health_grade', 'latest_health_grade_color'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']

    def get_latest_health_score(self, obj):
        """Get the latest health check score percentage"""
        latest_check = obj.health_checks.first()  # Already ordered by -created_at in model
        return latest_check.percentage if latest_check else None

    def get_latest_health_grade(self, obj):
        """Get the latest health check grade"""
        latest_check = obj.health_checks.first()
        return latest_check.grade if latest_check else None

    def get_latest_health_grade_color(self, obj):
        """Get the latest health check grade color"""
        latest_check = obj.health_checks.first()
        return latest_check.grade_color if latest_check else None


class DomainDetailSerializer(DomainSerializer):
    """Detailed serializer for Domain with related keywords"""
    keywords = serializers.SerializerMethodField()
    
    class Meta(DomainSerializer.Meta):
        fields = DomainSerializer.Meta.fields + ['keywords']
    
    def get_keywords(self, obj):
        from keywords.serializers import KeywordSerializer
        keywords = obj.keywords.all()
        return KeywordSerializer(keywords, many=True).data



class DomainAccessSerializer(serializers.ModelSerializer):
    """Serializer for DomainAccess"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    granted_by_email = serializers.CharField(source='granted_by.email', read_only=True)
    
    class Meta:
        model = DomainAccess
        fields = [
            'id', 'user', 'user_email', 'user_name', 'domain', 'domain_name',
            'granted_by', 'granted_by_email', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class DomainAccessCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating DomainAccess"""
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = DomainAccess
        fields = ['user_id']
    
    def create(self, validated_data):
        # Convert user_id to user object
        user_id = validated_data.pop('user_id')
        from authentication.models import Account
        validated_data['user'] = Account.objects.get(id=user_id)

        # Set granted_by to the current user from context
        validated_data['granted_by'] = self.context['request'].user
        return super().create(validated_data)


class InternalLinkMapSerializer(serializers.ModelSerializer):
    """Serializer for InternalLinkMap model"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = InternalLinkMap
        fields = [
            'id', 'domain', 'domain_name', 'topic', 'keywords', 'url',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class InternalLinkMapCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating InternalLinkMap entries"""

    class Meta:
        model = InternalLinkMap
        fields = ['topic', 'keywords', 'url']

    def validate_url(self, value):
        """Ensure URL is valid"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value


class ReferenceDocumentSerializer(serializers.ModelSerializer):
    """Serializer for ReferenceDocument model"""
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True, default='')
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ReferenceDocument
        fields = [
            'id', 'domain', 'file_name', 'file_type', 'file_size',
            'description', 'extracted_text',
            'uploaded_by', 'uploaded_by_email', 'uploaded_by_name',
            'file_url', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at', 'uploaded_by']

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}".strip() or obj.uploaded_by.email
        return ''

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
