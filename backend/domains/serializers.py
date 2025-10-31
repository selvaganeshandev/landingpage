from rest_framework import serializers
from .models import Domain, DomainAccess


class DomainSerializer(serializers.ModelSerializer):
    """Serializer for Domain model"""
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    
    class Meta:
        model = Domain
        fields = [
            'id', 'name', 'url', 'organisation', 'organisation_name',
            'total_mentions', 'total_citations', 'visibility_score', 
            'average_position', 'active_alerts', 'sentiment_category', 
            'sentiment_score', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


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
