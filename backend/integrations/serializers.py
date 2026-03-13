from rest_framework import serializers
from .models import Integration


class IntegrationSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Integration
        fields = [
            'id', 'domain', 'domain_name', 'type', 'provider_id', 'credentials',
            'status', 'last_sync_at', 'error_message', 'created_by',
            'created_by_email', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'last_sync_at', 'created_at', 'modified_at']
        extra_kwargs = {
            'credentials': {'write_only': True}  # Don't expose credentials in responses
        }


class IntegrationPublicSerializer(serializers.ModelSerializer):
    """Public serializer that doesn't expose sensitive credentials."""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    has_credentials = serializers.SerializerMethodField()

    class Meta:
        model = Integration
        fields = [
            'id', 'domain', 'domain_name', 'type', 'provider_id',
            'status', 'last_sync_at', 'error_message', 'has_credentials',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'last_sync_at', 'created_at', 'modified_at']

    def get_has_credentials(self, obj):
        """Check if the integration has OAuth tokens stored."""
        return bool(obj.credentials and obj.credentials.get('refresh_token'))

