from rest_framework import serializers
from .models import Keyword, SecondaryKeyword


class KeywordSerializer(serializers.ModelSerializer):
    """Serializer for Keyword model"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = Keyword
        fields = [
            'id', 'keyword', 'domain', 'domain_name',
            'volume_level', 'intent', 'entity', 'attribute', 'variable',
            'source', 'topic', 'cluster_id',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class SecondaryKeywordSerializer(serializers.ModelSerializer):
    """Serializer for SecondaryKeyword model"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = SecondaryKeyword
        fields = [
            'id', 'keyword', 'domain', 'domain_name',
            'volume_level', 'intent', 'entity', 'attribute', 'variable',
            'source', 'topic', 'cluster_id',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
