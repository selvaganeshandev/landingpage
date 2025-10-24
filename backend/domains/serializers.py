from rest_framework import serializers
from .models import Domain


class DomainSerializer(serializers.ModelSerializer):
    """Serializer for Domain model"""
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    
    class Meta:
        model = Domain
        fields = [
            'id', 'name', 'url', 'organisation', 'organisation_name',
            'total_mentions', 'total_citations', 'visibility_score', 
            'average_position', 'active_alerts', 'sentiment', 
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
