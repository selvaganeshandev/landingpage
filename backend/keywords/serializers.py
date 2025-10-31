from rest_framework import serializers
from .models import Keyword


class KeywordSerializer(serializers.ModelSerializer):
    """Serializer for Keyword model"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    
    class Meta:
        model = Keyword
        fields = [
            'id', 'keyword', 'domain', 'domain_name', 
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
